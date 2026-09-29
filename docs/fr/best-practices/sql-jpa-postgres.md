# Bonnes pratiques SQL, JPA & Postgres



## 🗺️ Mapping des entités

### Rendez toutes les associations `LAZY`
Mettez `fetch = FetchType.LAZY` sur `@ManyToOne` et `@OneToOne`. (`@OneToMany` et `@ManyToMany` sont déjà lazy.)

**Pourquoi c'est une bonne pratique :** `@ManyToOne` et `@OneToOne` sont `EAGER` par défaut. Chaque fois que vous
chargez une `Order`, Hibernate charge aussi son `Customer`, l'`Address` du client, et ainsi de suite, souvent avec
une requête supplémentaire par ligne. On ne peut pas désactiver le chargement eager pour une seule requête, mais on
peut toujours activer le chargement quand on en a besoin (fetch join, entity graph). Lazy par défaut, chargement
explicite par cas d'usage.

⛔ `@ManyToOne private Customer customer;`
✅ `@ManyToOne(fetch = FetchType.LAZY) private Customer customer;`

### Préférez `SEQUENCE` à `IDENTITY` pour les ids
Utilisez `@GeneratedValue(strategy = GenerationType.SEQUENCE)` avec un `allocationSize` égal à l'incrément de la
séquence.

**Pourquoi c'est une bonne pratique :** avec `IDENTITY`, l'id n'est connu qu'après l'`INSERT`, donc Hibernate doit
exécuter chaque insert immédiatement et ne peut pas les regrouper : enregistrer 10 000 lignes fait 10 000
allers-retours. Avec une séquence, Hibernate récupère les ids par blocs (`allocationSize = 50` → un appel à la
séquence toutes les 50 lignes) et envoie les inserts en batchs JDBC (`hibernate.jdbc.batch_size`). Les séquences
Postgres sont peu coûteuses et faites pour ça.

⛔ `@GeneratedValue(strategy = GenerationType.IDENTITY)`
✅ `@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_seq")` + `@SequenceGenerator(name = "order_seq", allocationSize = 50)`

### Implémentez `equals` / `hashCode` avec soin sur les entités
Basez-les sur une clé métier naturelle, ou sur l'id avec un `hashCode` constant. N'utilisez jamais `@Data` de
Lombok sur une entité.

**Pourquoi c'est une bonne pratique :** un id généré vaut `null` tant que l'entité n'est pas persistée. Si
`hashCode` utilise l'id, il change après `save()`, et une entité ajoutée à un `HashSet` avant l'enregistrement ne
peut plus y être retrouvée. `@Data` / `@EqualsAndHashCode` de Lombok inclut tous les champs, y compris les
collections lazy : appeler `hashCode` déclenche leur chargement, ou une `StackOverflowError` sur les relations
bidirectionnelles. Son `toString` a le même problème.

```java
// ✅ basé sur l'id, stable sur tout le cycle de vie de l'entité
@Override public boolean equals(Object o) {
    return o instanceof Order other && id != null && id.equals(other.id);
}
@Override public int hashCode() { return getClass().hashCode(); }
```

### Utilisez le verrouillage optimiste avec `@Version`
Ajoutez une colonne `@Version` aux entités qui peuvent être modifiées en parallèle.

**Pourquoi c'est une bonne pratique :** sans elle, deux utilisateurs chargent la même ligne, la modifient tous les
deux, et le second enregistrement écrase silencieusement le premier : une mise à jour perdue. Avec `@Version`,
Hibernate ajoute `WHERE version = ?` à l'update ; si quelqu'un a modifié la ligne entre-temps, 0 ligne ne
correspond et une `OptimisticLockException` est levée, ce qui permet de demander à l'utilisateur de recharger.
Cela coûte une colonne entière et aucun verrou.

✅ `@Version private long version;`

## ⚡ Requêtes & performance

### Évitez les requêtes N+1
Quand vous avez besoin d'une association pour une liste d'entités, chargez-la dans la même requête avec un
`JOIN FETCH` ou un `@EntityGraph`.

**Pourquoi c'est une bonne pratique :** charger 100 commandes puis appeler `order.getCustomer().getName()` dans une
boucle exécute 1 requête pour les commandes plus 100 pour les clients. C'est invisible dans le code et dans les
tests avec 3 lignes, et transforme une page de 10 ms en page de 2 s en production. Activez les logs SQL ou
utilisez une assertion sur le nombre de requêtes dans les tests pour le détecter. Pour les collections,
`@BatchSize` ou `hibernate.default_batch_fetch_size` réduit N à N / taille du batch.

```java
// ⛔ 1 + N requêtes
List<Order> orders = orderRepository.findAll();
orders.forEach(o -> print(o.getCustomer().getName()));

// ✅ une seule requête
@Query("select o from Order o join fetch o.customer")
List<Order> findAllWithCustomer();
```

### Lisez avec des projections, pas des entités
Pour les écrans et API en lecture seule, ne sélectionnez que les colonnes nécessaires dans un DTO ou une projection
par interface.

**Pourquoi c'est une bonne pratique :** charger des entités signifie sélectionner toutes les colonnes, créer des
objets managés, garder un snapshot de chacun pour le dirty checking, et faire un flush à la fin. Pour une page de
liste qui n'affiche que 3 champs, c'est de la mémoire et du CPU gaspillés. Une projection exécute une requête plus
étroite et renvoie des objets simples qu'Hibernate ne suit pas.

⛔ `List<Order> findByStatus(Status s)` puis mapper 3 champs
✅ `@Query("select new com.acme.OrderSummary(o.id, o.total, o.createdAt) from Order o where o.status = :s")`

### Utilisez la pagination par clé (keyset) pour les grandes tables
Pour une pagination profonde ou un scroll infini, paginez avec `WHERE id > :lastId ORDER BY id LIMIT n` plutôt
qu'avec un grand `OFFSET`.

**Pourquoi c'est une bonne pratique :** `OFFSET 100000` oblige Postgres à lire et jeter 100 000 lignes avant de
renvoyer la page, donc chaque page est plus lente que la précédente. Les lignes insérées ou supprimées entre deux
requêtes décalent aussi les pages, ce qui donne des doublons ou des éléments manquants. La pagination par clé
utilise l'index pour sauter directement à la ligne suivante : temps constant quelle que soit la page, et résultat
stable.

```sql
-- ⛔ de plus en plus lent à mesure que l'offset grandit
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000;

-- ✅ utilise l'index, temps constant
SELECT * FROM orders WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```

### Indexez les clés étrangères et les colonnes filtrées, et vérifiez avec `EXPLAIN`
Créez des index pour les colonnes utilisées dans `WHERE`, `JOIN` et `ORDER BY`, clés étrangères comprises.
Vérifiez le plan avec `EXPLAIN (ANALYZE, BUFFERS)`.

**Pourquoi c'est une bonne pratique :** Postgres indexe automatiquement les clés primaires et les contraintes
d'unicité, mais *pas* les clés étrangères. Une jointure sur `order_line.order_id` ou un `DELETE` sur la table
parente fait alors un parcours complet de la table enfant. Deviner n'est pas fiable : `EXPLAIN ANALYZE` montre si
l'index est utilisé (`Index Scan`) ou non (`Seq Scan`) et où part le temps. N'indexez pas tout non plus : chaque
index ralentit les écritures.

⛔ `order_line.order_id` sans index
✅ `CREATE INDEX idx_order_line_order_id ON order_line (order_id);`

### Utilisez toujours des paramètres liés
Passez les valeurs en paramètres (`?`, `:name`), jamais en les concaténant dans la chaîne SQL.

**Pourquoi c'est une bonne pratique :** la concaténation, c'est l'injection SQL : `name = "x' OR '1'='1"` renvoie
toutes les lignes, et des payloads pires suppriment des tables ou lisent les données d'autres utilisateurs. Les
paramètres liés sont envoyés séparément du texte SQL, donc ils sont toujours traités comme des valeurs. Ils
permettent aussi à la base de réutiliser le plan d'exécution. Cela s'applique aussi au JPQL et aux requêtes
natives.

⛔ `em.createQuery("from User where name = '" + name + "'")`
✅ `em.createQuery("from User where name = :name").setParameter("name", name)`

### Gardez les transactions courtes
Ouvrez une transaction, faites le travail en base, commitez. Pas de saisie utilisateur, d'appels distants ou de
longs calculs entre les deux.

**Pourquoi c'est une bonne pratique :** une longue transaction garde ses verrous de lignes, ce qui bloque les
autres écritures, et empêche le `VACUUM` de Postgres de nettoyer les lignes mortes qu'elle pourrait encore avoir
besoin de voir, donc les tables et les index gonflent. Une connexion laissée `idle in transaction` garde tout
ouvert indéfiniment. Configurez `idle_in_transaction_session_timeout` comme filet de sécurité.

⛔ appeler une API de paiement dans la transaction
✅ commiter d'abord, puis appeler l'API, puis enregistrer le résultat dans une seconde transaction courte

## 🐘 Types & schéma Postgres

### Utilisez `timestamptz`, `numeric` et `text`
Stockez les instants en `timestamptz`, l'argent en `numeric(p, s)`, et les chaînes en `text` (ou `varchar(n)`
seulement quand la limite est une vraie règle).

**Pourquoi c'est une bonne pratique :** `timestamp` (sans fuseau) stocke une heure « murale » sans fuseau : la
même valeur désigne des instants différents sur des serveurs configurés différemment, et les changements d'heure
créent des doublons. `timestamptz` stocke un instant absolu (en UTC) et se mappe sur `Instant` /
`OffsetDateTime`. `real` / `double precision` ont les mêmes erreurs d'arrondi que le `double` Java ; `numeric`
est exact et se mappe sur `BigDecimal`. Dans Postgres, `text` et `varchar` ont les mêmes performances, donc un
`varchar(255)` arbitraire n'ajoute qu'une limite qui cassera plus tard.

⛔ `created_at timestamp`, `amount double precision`
✅ `created_at timestamptz`, `amount numeric(19, 4)`

### Mettez les règles d'intégrité dans la base
Déclarez les contraintes `NOT NULL`, `UNIQUE`, `FOREIGN KEY` et `CHECK` dans le schéma, pas seulement dans le code
applicatif.

**Pourquoi c'est une bonne pratique :** les vérifications applicatives sont sujettes aux race conditions : deux
requêtes vérifient toutes les deux « email non utilisé » et insèrent toutes les deux. Une contrainte `UNIQUE` ne
peut pas être contournée, quel que soit le chemin (un batch, une correction manuelle dans `psql`, un autre
service). Les contraintes documentent aussi le modèle pour quiconque lit le schéma, et le planificateur s'en sert.

⛔ `if (!repository.existsByEmail(email)) repository.save(user);` seul
✅ `ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);` + gérer la violation

## 🚚 Migrations

### Versionnez le schéma avec Flyway ou Liquibase
Chaque modification du schéma est un fichier de migration dans le dépôt. N'utilisez jamais `ddl-auto=update` (ou
`create`) en dehors du développement local.

**Pourquoi c'est une bonne pratique :** `ddl-auto=update` devine les changements à partir de vos entités : il ne
supprime ni ne renomme jamais rien, ne sait pas migrer les données, et exécute un SQL différent selon l'état de
chaque base. Les environnements divergent et personne ne sait à quoi ressemble la production. Les migrations sont
relues, reproductibles, exécutées dans l'ordre, et enregistrées dans une table d'historique. Mettez
`ddl-auto=validate` pour que l'application échoue au démarrage si les entités et le schéma ne correspondent pas.

⛔ `spring.jpa.hibernate.ddl-auto: update`
✅ `db/migration/V12__add_order_status.sql` + `ddl-auto: validate`

### Écrivez des migrations qui ne bloquent pas la production
Créez les index avec `CREATE INDEX CONCURRENTLY`, ajoutez les colonnes nullable (ou avec une valeur par défaut
constante), et découpez les changements cassants en étapes expand / contract.

**Pourquoi c'est une bonne pratique :** un `CREATE INDEX` simple bloque toutes les écritures sur la table pendant
toute la construction, ce qui peut prendre des minutes sur une grosse table. `CONCURRENTLY` ne les bloque pas (il
ne peut pas s'exécuter dans une transaction, donc configurez l'outil de migration en conséquence). Renommer ou
supprimer une colonne que la version en cours utilise encore la casse pendant le déploiement progressif : ajoutez
la nouvelle colonne, déployez du code qui écrit dans les deux, remplissez-la, basculez les lectures, puis
supprimez l'ancienne.

⛔ `CREATE INDEX idx_orders_status ON orders (status);`
✅ `CREATE INDEX CONCURRENTLY idx_orders_status ON orders (status);`
