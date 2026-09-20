# Persistance & SQL

## 🟢 Fondamentaux

### Choix d'ORM & d'accès aux données

#### Q1. Qu'est-ce qu'un ORM, et quel problème résout-il réellement ?
**Réponse :** Un ORM (Object-Relational Mapper) comble le « décalage d'impédance » entre le modèle relationnel
(tables, lignes, clés étrangères) et le modèle objet (classes, références, héritage) — en mappant
les lignes vers des objets, les clés étrangères vers des références/collections d'objets, et en traduisant la
navigation dans le graphe d'objets en jointures SQL ou en requêtes supplémentaires. Il résout le côté fastidieux et
sujet aux erreurs de l'écriture manuelle de ce code de mapping pour chaque entité, au prix de la génération
occasionnelle d'un SQL moins efficace qu'une requête écrite à la main pour un cas précis (voir le problème N+1, Q18).

**Exemple :**
```java
@Entity
class Order {
    @Id Long id;
    @ManyToOne Customer customer;       // clé étrangère -> référence objet
    @OneToMany(mappedBy = "order") List<LineItem> items; // jointure -> navigation dans une collection
}

order.getCustomer().getName();  // ressemble à un accès de champ...
order.getItems().size();        // ...mais chacun de ces appels peut déclencher silencieusement sa propre requête SQL
```

**Pourquoi c'est un piège :** traiter l'ORM comme « aucune connaissance SQL requise » est la réponse superficielle —
l'abstraction est réelle, mais elle fuit exactement là où la performance compte, et les deux lignes ci-dessus
sont précisément l'endroit où naît le problème N+1 (Q18).

#### Q2. Quand choisiriez-vous JPA/Hibernate, JDBC pur ou MyBatis ?
**Réponse :** JPA/Hibernate est le choix par défaut pour les applications typiques à forte dominante CRUD : on obtient le mapping
objet-relationnel, une abstraction de repository, des méthodes de requête dérivées, et on n'écrit pas de SQL à la main pour les cas
courants. JDBC pur (via `JdbcTemplate`) est plus bas niveau mais évite complètement la mécanique de l'ORM — utile
pour les chemins simples et très performants ou quand le SQL généré par l'ORM est le problème, et non la
solution. MyBatis se situe entre les deux : vous écrivez le SQL vous-même (contrôle total sur la requête exacte,
facile à optimiser) mais MyBatis gère le binding des paramètres et le mapping du result set vers les
objets — c'est le choix courant quand les requêtes sont complexes, critiques pour la performance, ou doivent utiliser
des fonctionnalités spécifiques à la base que l'ORM abstrait.

**Exemple :**
```java
// JPA/Hibernate : requête dérivée, aucun SQL écrit.
public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByCustomerIdAndStatus(Long customerId, String status);
}

// JDBC pur via JdbcTemplate : contrôle total, abstraction minimale.
List<Order> orders = jdbcTemplate.query(
    "select * from orders where customer_id = ? and status = ?",
    (rs, rowNum) -> mapOrder(rs), customerId, status);

// MyBatis : le SQL est écrit par vous, le mapping est géré par MyBatis.
@Select("select * from orders where customer_id = #{customerId} and status = #{status}")
List<Order> findByCustomerAndStatus(@Param("customerId") Long customerId, @Param("status") String status);
```

**Pourquoi c'est un piège :** « toujours utiliser JPA, c'est le standard » ignore le cas qui se présente réellement en
pratique — une requête de reporting avec une window function, un hint spécifique à la base, ou une jointure
optimisée à la main qu'Hibernate ne générerait jamais seul. Savoir quand *ne pas* recourir à l'ORM fait
partie de la réponse, ce n'est pas une concession.

### Bases du relationnel

#### Q3. Quelle est la différence entre une clé primaire, une contrainte d'unicité et un index ?
**Réponse :** Une clé primaire identifie chaque ligne de manière unique, est implicitement `NOT NULL`, et une table n'en a qu'une
au maximum ; elle crée aussi implicitement un index pour garantir et accélérer cette unicité. Une contrainte
d'unicité impose l'unicité sur une ou plusieurs colonnes mais autorise `NULL` (et autorise généralement
plusieurs `NULL`, puisque `NULL` n'est pas considéré comme égal à un autre `NULL`) — une table peut en avoir
plusieurs. Un index est uniquement une structure de données pour une recherche rapide sur une colonne (ou plusieurs) et
n'impose rien par lui-même ; les clés primaires et les contraintes d'unicité créent des index
comme effet de bord de l'application de leur contrainte, mais on peut aussi créer un index sans aucune
contrainte d'unicité, uniquement pour la vitesse des requêtes.

**Exemple :**
```sql
create table users (
    id bigint primary key,               -- unique + NOT NULL, index créé automatiquement
    email varchar(255) unique,           -- unique, mais NULL autorisé (et plus d'un NULL)
    last_login timestamp
);

create index idx_users_last_login on users(last_login); -- pure vitesse de recherche, aucune contrainte

insert into users (id, email) values (1, null); -- ok
insert into users (id, email) values (2, null); -- ok aussi — deux NULL ne violent pas l'unicité
```

**Pourquoi c'est un piège :** supposer qu'une contrainte d'unicité se comporte exactement comme une clé primaire, y compris pour
la gestion de `NULL` — si la règle métier exige aussi d'imposer « au plus une ligne avec un email *manquant* »,
une simple contrainte d'unicité n'y suffira pas ; cela demande une condition explicite ou un
choix de modélisation différent, pas une confiance aveugle dans la sémantique `NULL` par défaut de la contrainte.

#### Q4. Détaillez la normalisation d'une table de la 1NF à la 3NF.
**Réponse :** Soit une table plate `Orders` avec les colonnes `order_id, customer_name, customer_email, product_name,
product_price, quantity` : la **1NF** exige des valeurs atomiques et aucun groupe répétitif — si une colonne
stockait une liste de produits séparés par des virgules par commande, la scinder en une ligne par ligne de
commande produit est l'étape 1NF. La **2NF** exige que chaque colonne non-clé dépende de la clé primaire *entière*,
et non d'une partie — si la clé est `(order_id, product_id)` mais que `customer_name` ne dépend que de
`order_id`, c'est une dépendance partielle ; déplacez les données client dans leur propre table `Customers` clé
par `customer_id`. La **3NF** exige de supprimer les dépendances transitives — si `product_price` dans la
ligne de commande dépend de `product_id`, qui ne dépend de la clé de la ligne de commande que transitivement
via le produit, déplacez aussi `product_name`/`product_price` dans leur propre table `Products`. L'état
final : `Orders`, `Customers`, `Products`, et une table de jonction `OrderItems`, chaque colonne
ne dépendant que de la clé complète de sa propre table.

**Exemple :**
```sql
-- Avant (violation de la 1NF) : produits stockés comme groupe répétitif dans une seule colonne.
-- order_id | customer_name | customer_email | products
-- 1        | Ann           | ann@x.com      | "Widget,Gadget"

-- Après 3NF :
create table customers (customer_id bigint primary key, name text, email text);
create table products  (product_id  bigint primary key, name text, price numeric);
create table orders    (order_id    bigint primary key, customer_id bigint references customers);
create table order_items (
    order_id   bigint references orders,
    product_id bigint references products,
    quantity   int,
    primary key (order_id, product_id)
);
```

**Pourquoi c'est un piège :** « plus de tables, c'est toujours mieux » est la mauvaise conclusion — la normalisation existe pour
supprimer les anomalies de mise à jour/insertion/suppression, elle n'est pas une fin en soi ; un chemin très lu qui paie
une jointure sur quatre tables à chaque requête à cause d'une normalisation de manuel, alors que les données changent
à peine, est exactement le cas où la dénormalisation délibérée (Q33) est le choix le plus senior.

#### Q5. Que garantissent réellement les propriétés ACID ?
**Réponse :** **Atomicité** : les opérations d'une transaction réussissent toutes ou sont toutes annulées (rollback) ensemble, sans
application partielle. **Cohérence** : une transaction fait passer la base d'un état valide à un autre,
en respectant les contraintes (clés étrangères, contraintes d'unicité, contraintes check). **Isolation** :
les transactions concurrentes ne voient pas l'état intermédiaire non validé les unes des autres, dans une mesure
contrôlée par le niveau d'isolation (Q15). **Durabilité** : une fois validées (commit), les changements d'une transaction
survivent à un crash — généralement grâce à un write-ahead log vidé sur disque avant que le commit soit acquitté.

**Exemple :**
```sql
begin;
update accounts set balance = balance - 100 where id = 1;
update accounts set balance = balance + 100 where id = 2;
-- Si le processus plante ici, l'atomicité garantit qu'aucune des deux mises à jour ne survit au redémarrage.
commit; -- la durabilité garantit que les deux mises à jour survivent à tout crash à partir de ce point.
```

**Pourquoi c'est un piège :** le « C » est celui que les candidats formulent mal — il ne signifie pas « ma logique métier
est correcte », il signifie que la base impose les contraintes qu'on lui a explicitement déclarées
(clés étrangères, checks, unicité). Une transaction peut être parfaitement conforme ACID et laisser quand même
les données dans un état qui viole un invariant que le schéma n'a jamais déclaré — cet écart est un
bug applicatif, pas quelque chose qu'ACID ait jamais promis de détecter.

### SQL

#### Q6. Quelle est la différence entre `INNER JOIN` et `LEFT JOIN`, et pourquoi une clause `WHERE` peut-elle silencieusement transformer un `LEFT JOIN` en jointure interne ?
**Réponse :** `INNER JOIN` ne retourne que les lignes qui ont une correspondance des deux côtés. `LEFT JOIN` retourne
*chaque* ligne de la table de gauche et remplit les colonnes de la table de droite avec `NULL` quand aucune correspondance
n'existe — l'outil pour des questions comme « tous les clients, y compris ceux sans commande ». Le point subtil
est l'endroit où placer le filtre. Une condition dans la clause `ON` est appliquée *pendant la mise en correspondance*, donc les
lignes de gauche sans correspondance survivent avec des `NULL`. Une condition sur une colonne de la table de droite dans la clause
`WHERE` est appliquée *après* la jointure, et comme `NULL = 'PAID'` n'est pas vrai, les lignes sans correspondance sont
filtrées — la requête se comporte discrètement comme une jointure interne. (Filtrer sur la table de *gauche* dans
`WHERE` est toujours correct ; et `WHERE o.id IS NULL` est l'idiome d'anti-jointure délibéré pour « les clients
sans commande ».)

**Exemple :**
```sql
-- Objectif : chaque client avec son nombre de commandes PAID, y compris les clients sans commande (0).

-- Faux : le WHERE supprime les clients sans commande -> ils disparaissent du rapport.
select c.id, count(o.id)
from customers c
left join orders o on o.customer_id = c.id
where o.status = 'PAID'
group by c.id;

-- Correct : la condition appartient au ON, donc les clients sans correspondance sont conservés avec count = 0.
select c.id, count(o.id)
from customers c
left join orders o on o.customer_id = c.id and o.status = 'PAID'
group by c.id;
```

**Pourquoi c'est un piège :** la requête fausse retourne des données plausibles sans aucune erreur — un rapport qui
omet « simplement » les clients avec zéro commande, découvert des semaines plus tard quand les totaux ne concordent pas.
Notez aussi `count(o.id)` plutôt que `count(*)` : `count(*)` compterait la ligne complétée de `NULL` comme 1.

#### Q7. Quelle est la différence entre `UNION` et `UNION ALL`, et lequel devrait être votre choix par défaut ?
**Réponse :** Les deux empilent les résultats de deux requêtes ayant le même nombre de colonnes et des types
compatibles. `UNION` **supprime en plus les lignes en double** du résultat combiné, ce que la
base implémente avec un tri ou un hash aggregate sur *toute* la sortie — CPU et mémoire supplémentaires
(avec un éventuel débordement sur disque) et aucune ligne retournée tant que cette étape n'est pas terminée. `UNION ALL` se contente
de concaténer et de streamer. `UNION ALL` est donc le bon choix par défaut, et `UNION` est un choix délibéré
pour le cas où la même ligne peut réellement provenir des deux côtés et où on la veut une seule fois. Deux points connexes :
les *noms* de colonnes viennent de la première requête, et `INTERSECT`/`EXCEPT` sont les opérateurs ensemblistes
pour « dans les deux » et « dans la première mais pas dans la seconde » (ils dédupliquent aussi, sauf si `ALL`
est précisé).

**Exemple :**
```sql
-- Les commandes actives et archivées vivent dans deux tables avec des ids disjoints : aucun doublon possible.
select id, customer_id, total from orders
union all                                   -- économique : pas de passe de déduplication
select id, customer_id, total from orders_archive;

-- Le même client peut apparaître dans les deux listes et on veut chacun une seule fois -> UNION est délibéré ici.
select customer_id from newsletter_subscribers
union
select customer_id from recent_buyers;
```

**Pourquoi c'est un piège :** écrire `UNION` « parce que c'est celui que tout le monde connaît » ajoute discrètement un
tri sur des millions de lignes et — pire — peut *changer les résultats* : il fusionne des lignes légitimement
répétées (deux lignes de vente identiques) qu'un rapport devait additionner.

## 🟡 Pièges seniors

### Sémantique SQL

#### Q8. Quel est l'ordre d'exécution logique des clauses d'une requête SQL — et pourquoi ne peut-on pas filtrer sur un alias de `SELECT` dans `WHERE` ?
**Réponse :** `FROM`/`JOIN` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `DISTINCT` → `ORDER BY` →
`LIMIT`/`OFFSET`. C'est l'ordre de traitement logique sur lequel raisonne le moteur, pas l'ordre dans lequel
on tape physiquement les clauses. Le piège : essayer de filtrer sur un alias de colonne défini dans
`SELECT` depuis `WHERE` échoue dans la plupart des bases, précisément parce que `WHERE` est logiquement
évalué *avant* `SELECT` — l'alias n'existe pas encore à ce stade de l'exécution logique.
`ORDER BY`, à l'inverse, s'exécute après `SELECT` et *peut* donc référencer un alias de `SELECT`.

**Exemple :**
```sql
select price * quantity as line_total
from order_items
where line_total > 100;   -- ERREUR : la colonne "line_total" n'existe pas — WHERE s'exécute avant SELECT

select price * quantity as line_total
from order_items
order by line_total desc; -- correct — ORDER BY s'exécute après SELECT, l'alias existe déjà

select price * quantity as line_total
from order_items
where price * quantity > 100; -- la vraie solution : répéter l'expression, ne pas compter sur l'alias
```

**Pourquoi c'est un piège :** les candidats qui ont mémorisé « on ne peut pas utiliser un alias de `SELECT` dans `WHERE` » comme
règle savent rarement *pourquoi* — et le même ordre sous-jacent est ce qui fait fonctionner `HAVING` (Q9) là où
`WHERE` ne le peut pas, et pourquoi une window function ne peut pas non plus apparaître dans `WHERE`. C'est un seul modèle mental,
pas trois règles de syntaxe sans rapport à mémoriser séparément.

#### Q9. Pourquoi peut-on filtrer sur une fonction d'agrégation dans `HAVING` mais pas dans `WHERE` ?
**Réponse :** Parce que `WHERE` est évalué avant que le regroupement/l'agrégation n'ait lieu (selon l'ordre de la Q8), donc les
valeurs d'agrégat comme `COUNT(*)` ou `SUM(x)` n'existent pas encore à ce stade du traitement — il n'y a rien
sur quoi filtrer. `HAVING` s'exécute après `GROUP BY`, une fois les agrégats réellement calculés par
groupe, c'est donc le bon endroit pour filtrer dessus (`HAVING COUNT(*) > 5`). `WHERE` filtre toujours
les lignes individuelles avant le regroupement ; `HAVING` filtre les groupes après le regroupement — utiliser la mauvaise clause
échoue net ou, pire, calcule silencieusement autre chose que ce qui était voulu.

**Exemple :**
```sql
select customer_id, count(*) as order_count
from orders
where count(*) > 5   -- ERREUR : les fonctions d'agrégation ne sont pas autorisées dans WHERE
group by customer_id;

select customer_id, count(*) as order_count
from orders
group by customer_id
having count(*) > 5; -- correct : filtre les groupes, évalué après le calcul de l'agrégat
```

**Pourquoi c'est un piège :** l'échec n'est pas toujours une erreur de syntaxe nette qu'un candidat peut simplement corriger et
oublier — confondre la clause qui restreint les *lignes* et celle qui restreint les *groupes* peut produire une requête
qui s'exécute et retourne un nombre plausible mais silencieusement faux, ce qui est un bug de production bien pire
qu'un échec bruyant au moment de la requête.

#### Q10. Quels sont les pièges classiques de `NULL` en SQL, et comment éviter chacun ?
**Réponse :** SQL utilise une logique à trois valeurs : une comparaison impliquant `NULL` n'est ni vraie ni fausse mais
*inconnue*, et une clause `WHERE` ne garde que les lignes dont la condition est *vraie*. Conséquences :
(1) `col = NULL` et `col <> NULL` ne correspondent jamais à rien — utilisez `IS NULL` / `IS NOT NULL`, ou
`IS DISTINCT FROM` pour une comparaison sûre vis-à-vis de `NULL`. (2) `col <> 'X'` **exclut** silencieusement les lignes
où `col` vaut `NULL`, donc « tout sauf X » n'est pas tout. (3) `x NOT IN (subquery)`
ne retourne **aucune ligne** si la sous-requête produit ne serait-ce qu'un `NULL`, car `x <> NULL` est
inconnu pour tout `x` ; utilisez `NOT EXISTS`, qui est sûr vis-à-vis de `NULL`. (4) Les agrégats ignorent les `NULL` :
`count(col)` compte les valeurs non nulles tandis que `count(*)` compte les lignes, et `avg(col)` divise par le
nombre de non-null uniquement. (5) Dans `ORDER BY`, PostgreSQL trie les `NULL` en *dernier* en croissant et en *premier*
en décroissant — utilisez `NULLS FIRST/LAST` explicitement. (6) Une contrainte `UNIQUE` traite les `NULL` comme
distincts, donc de nombreuses lignes avec `NULL` sont autorisées ; PostgreSQL 15+ propose `UNIQUE NULLS NOT DISTINCT`
quand on en veut au plus un. `COALESCE` fournit une valeur par défaut quand on veut vraiment que `NULL` soit traité comme une
valeur.

**Exemple :**
```sql
-- customers: 1, 2, 3        orders.customer_id: 1, NULL   (un checkout invité sans client)

select id from customers where id not in (select customer_id from orders);
-- ne retourne AUCUNE ligne (2 et 3 attendus) : 2 <> NULL est inconnu, donc le NOT IN n'est jamais vrai

select id from customers c
where not exists (select 1 from orders o where o.customer_id = c.id);   -- retourne 2, 3

select count(*), count(customer_id) from orders;      -- 2, 1
select * from tickets where status <> 'CLOSED';       -- manque les tickets dont le status est NULL
select * from tickets where status is distinct from 'CLOSED';  -- les inclut
```

**Pourquoi c'est un piège :** chacun de ces cas retourne des données fausses sans erreur, et `NOT IN` est
correct sur des données de test sans `NULL` — il casse le jour où une colonne nullable reçoit son premier
`NULL` en production (voir S17).

#### Q11. Pourquoi la pagination par `OFFSET` devient-elle plus lente — et moins correcte — à mesure qu'on va en profondeur, et quelle est l'alternative ?
**Réponse :** `OFFSET n LIMIT m` ne peut pas sauter directement à la ligne `n` : la base doit produire puis jeter les
`n` premières lignes dans l'ordre demandé, donc la page 20 000 coûte 20 000 × taille-de-page lignes de travail alors même
que seules `m` sont retournées — la latence croît linéairement avec la profondeur et la charge sur la base augmente
avec chaque bot qui crawle jusqu'à la dernière page. Elle est aussi **instable** : si des lignes sont insérées ou
supprimées entre deux requêtes, tout se décale et le client voit des doublons ou manque des lignes
complètement. La **pagination keyset (seek)** corrige les deux : le client envoie la *dernière ligne qu'il a vue* et la
requête dit « donne-moi les lignes après cette clé », ce qu'un index satisfait directement en O(taille de page)
quelle que soit la profondeur. Les prérequis sont un **ordre total déterministe** — un
départage unique tel que `id` ajouté à la colonne de tri, sinon les lignes de timestamps égaux sont
sautées ou répétées — un index composite correspondant, et l'acceptation du compromis : on peut aller à
suivant/précédent mais pas sauter à la « page 137 », et un `count(*)` pour « 1–50 sur 4 231 987 » est une
requête distincte (et elle-même coûteuse), souvent remplacée par « a une suite » ou un comptage approximatif.

**Exemple :**
```sql
-- Offset : lit et jette 1 000 000 lignes pour en retourner 50.
select id, created_at, payload
from events
order by created_at desc, id desc
offset 1000000 limit 50;

-- Keyset : le client transmet le dernier (created_at, id) reçu.
create index events_seek_idx on events (created_at desc, id desc);

select id, created_at, payload
from events
where (created_at, id) < (:last_created_at, :last_id)   -- comparaison de row-values
order by created_at desc, id desc
limit 50;
```

**Pourquoi c'est un piège :** la pagination par offset est rapide sur la table de 500 lignes d'un développeur et c'est le défaut de
tous les frameworks (`Pageable`), donc elle part en production. L'échec arrive à la fois comme un problème de performance
et comme des doublons/lignes manquantes silencieux dans un export ou un scroll infini — et l'instinct « il suffit d'ajouter un index »
n'aide pas dans le cas de l'offset (S18).

### Indexation & plans de requête

#### Q12. Quels types d'index PostgreSQL offre-t-il au-delà du B-tree par défaut, et quand recourir à chacun ?
**Réponse :** Le B-tree (par défaut) gère les requêtes d'égalité et de plage (`=`, `<`, `>`, `BETWEEN`, tri) et
couvre la grande majorité des cas. GIN (Generalized Inverted Index) indexe les données composites/multi-
valuées — colonnes `tsvector` de recherche plein texte, inclusion de tableaux (`@>`), et notamment
les colonnes `JSONB` pour les requêtes d'inclusion/d'existence de clé (`jsonb_column @> '{"key": "value"}'`),
qu'un B-tree ne peut pas indexer utilement. GiST supporte les requêtes géométriques/de chevauchement de plages. Un **index
partiel** (`CREATE INDEX ... WHERE status = 'active'`) n'indexe que les lignes satisfaisant une condition —
bien plus petit et plus rapide qu'un index complet quand les requêtes filtrent toujours sur un sous-ensemble restreint et bien défini
d'une grande table (par ex. uniquement les lignes « active » d'une table majoritairement archivée).

**Exemple :**
```sql
create index idx_orders_created_at on orders(created_at);                 -- B-tree : par défaut
create index idx_products_attrs   on products using gin (attributes);     -- GIN : inclusion JSONB
create index idx_bookings_period  on bookings using gist (during);        -- GiST : chevauchement de plages
create index idx_orders_active    on orders(customer_id) where status = 'active'; -- partiel
```

**Pourquoi c'est un piège :** recourir à un index GIN sur chaque colonne `JSONB` « au cas où » ignore que
les index GIN sont nettement plus coûteux à maintenir en écriture qu'un B-tree — en appliquer un partout
sans vérifier le pattern de requête réel sacrifie le débit d'écriture au profit d'une vitesse de recherche que personne
n'a demandée sur cette colonne.

#### Q13. Pourquoi l'ordre des colonnes compte-t-il dans un index composite (multi-colonnes) ?
**Réponse :** Un index composite B-tree sur `(a, b)` est physiquement trié d'abord par `a`, puis par `b` au sein de chaque valeur de `a`
— il peut donc servir efficacement une requête filtrant sur `a` seul, ou sur `a` et `b` ensemble,
mais il est largement inutile pour une requête filtrant sur `b` seul (l'index n'a aucun ordre utile sur
`b` isolément, ce qui force un scan complet de l'index ou de la table). La règle empirique : placer en premier la
colonne avec des filtres d'égalité et la plus haute sélectivité (celle qui réduit le plus les résultats), et
les colonnes utilisées pour des filtres de plage ou fréquemment interrogées sans les autres colonnes devraient
généralement venir après ou avoir leur propre index séparé — et toujours vérifier avec `EXPLAIN` plutôt que
de supposer, car le bon ordre dépend aussi des patterns de requête réels.

**Exemple :**
```sql
create index idx_orders_customer_status on orders(customer_id, status);

-- Utilise l'index efficacement — filtre sur la colonne de tête :
select * from orders where customer_id = 42;
select * from orders where customer_id = 42 and status = 'PENDING';

-- Ne peut pas utiliser cet index efficacement — status n'est pas la colonne de tête :
select * from orders where status = 'PENDING';
```

**Pourquoi c'est un piège :** « il suffit d'ajouter un index composite sur chaque colonne filtrée par la requête » sans
vérifier l'ordre des colonnes par rapport à la forme réelle de la requête produit un index qui ne
sert silencieusement pas la requête pour laquelle il a été ajouté — `EXPLAIN` montre toujours un `Seq Scan`, et l'index reste
là à payer son coût d'écriture pour rien.

#### Q14. Comment lisez-vous la sortie de `EXPLAIN ANALYZE` pour diagnostiquer une requête lente ?
**Réponse :** `EXPLAIN ANALYZE` exécute réellement la requête et montre le vrai plan d'exécution avec les nombres de lignes
réels et le timing par étape, imbriqué du plus interne vers l'extérieur. La première chose à vérifier : un `Seq Scan` (scan complet
de la table) sur une grande table là où un `Index Scan` était attendu — cela signifie généralement un index manquant,
une fonction appliquée à la colonne indexée empêchant l'usage de l'index (`WHERE lower(email) = ...`
sans index fonctionnel correspondant), ou l'estimation de coût du planner qui favorise réellement un scan
(courant quand la sélectivité est mauvaise — le filtre ne réduit pas vraiment beaucoup de lignes). Deuxièmement :
comparer le nombre de lignes estimé par le planner au nombre réel à chaque étape — un grand
écart signifie des statistiques de table obsolètes (`ANALYZE` doit tourner) qui induisent le planner en erreur vers un
mauvais plan. Troisièmement : chercher un `Nested Loop` sur un grand ensemble externe — souvent la forme de plan
derrière un problème de type N+1 au niveau SQL lui-même.

**Exemple :**
```
Seq Scan on orders  (cost=0.00..48123.00 rows=1 width=64) (actual time=0.02..412.55 rows=980000 loops=1)
  Filter: (customer_id = 42)
  Rows Removed by Filter: 19020000
Planning Time: 0.15 ms
Execution Time: 415.10 ms
```
Un `Seq Scan` parcourant 20 millions de lignes pour en retourner 980 000 qui correspondent à un seul `customer_id`, alors que
le planner n'avait estimé qu'1 ligne — cet écart estimation/réel pointe directement vers des statistiques
obsolètes, et le scan complet lui-même pointe vers un index manquant sur `customer_id`.

**Pourquoi c'est un piège :** `EXPLAIN` sans `ANALYZE` ne montre que le coût et les nombres de lignes *estimés* par le planner
— il n'exécute jamais la requête. Citer ces chiffres comme s'il s'agissait de timings réellement mesurés est le signe qu'un candidat n'a pas
réellement exécuté ni lu un vrai plan `ANALYZE` sur des données à l'échelle de la production.

### Transactions & concurrence

#### Q15. Nommez les niveaux d'isolation des transactions et les anomalies que chacun prévient.
**Réponse :** Du plus lâche au plus strict : **Read Uncommitted** ne prévient rien (dirty reads possibles ; rarement
utilisé, PostgreSQL le traite de façon identique à Read Committed). **Read Committed** (le défaut de
PostgreSQL) prévient les dirty reads (ne voit jamais les changements non validés d'une autre transaction) mais autorise
les non-repeatable reads (relire la même ligne dans une transaction peut donner une valeur différente, désormais
validée) et les phantom reads (une requête de plage répétée peut retourner des lignes différentes).
**Repeatable Read** prévient en plus les non-repeatable reads en prenant un snapshot cohérent
pour toute la transaction — dans PostgreSQL spécifiquement, cela prévient aussi les phantom reads (contrairement à
la garantie minimale du standard SQL), au prix toutefois d'éventuels échecs de sérialisation
en cas de conflits d'écriture qui doivent être rejoués. **Serializable** garantit que le résultat est
équivalent à *une* exécution série (une à la fois) de toutes les transactions concurrentes — la
garantie la plus forte, au coût le plus élevé en contention et en taux de retry.

**Exemple :**
```sql
-- Session A (Read Committed, défaut de PostgreSQL)
begin;
select balance from accounts where id = 1; -- retourne 100

-- Session B, commit en concurrence
update accounts set balance = 50 where id = 1;
commit;

-- de retour dans la Session A, même transaction :
select balance from accounts where id = 1; -- retourne 50 — un non-repeatable read
commit;
```

**Pourquoi c'est un piège :** traiter « une isolation plus haute est strictement plus sûre » comme la règle ignore le
coût en débit — mettre par défaut chaque transaction en `SERIALIZABLE` « par sécurité » échange une anomalie précise et
comprise contre un taux bien plus élevé d'échecs de sérialisation que chaque chemin de code doit désormais
rejouer, ce qui est souvent un résultat de production pire que l'anomalie qu'on voulait éviter.

#### Q16. Expliquez le locking optimiste vs pessimiste en termes de contention réelle, pas seulement de définitions.
**Réponse :** Le locking pessimiste acquiert un lock au niveau base (`SELECT ... FOR UPDATE`) dès qu'une ligne est
lue en vue d'une mise à jour, empêchant toute autre transaction de la modifier (parfois même de la lire) jusqu'à ce que
la première transaction fasse commit ou rollback — correct sous forte contention sur les mêmes lignes,
mais il sérialise les accès et peut créer des attentes de lock ou des deadlocks sous charge. Le locking optimiste
ajoute une colonne de version (`@Version`) et vérifie au moment du commit si la version de la ligne correspond toujours à
ce qui a été lu — si une autre transaction l'a mise à jour entre-temps, le commit échoue avec une
`OptimisticLockException` au lieu de bloquer qui que ce soit. Il passe bien mieux à l'échelle sous *faible*
contention (aucun lock détenu pendant que l'utilisateur « réfléchit »), mais sous une contention réellement forte
sur les mêmes lignes, il ne fait que déplacer le coût du blocage vers un fort taux de commits échoués
à rejouer — à un certain niveau de contention, le locking pessimiste est en fait le
meilleur choix de débit, pas l'option naïvement « pire ».

**Exemple :**
```java
// Pessimiste : empêche toute autre transaction de toucher cette ligne jusqu'au commit/rollback.
Account acct = em.createQuery("select a from Account a where a.id = :id", Account.class)
    .setParameter("id", id)
    .setLockMode(LockModeType.PESSIMISTIC_WRITE)
    .getSingleResult();

// Optimiste : aucun lock détenu ; échoue au commit si la version a changé entre-temps.
@Entity
class Account {
    @Version private long version;
    private BigDecimal balance;
}
// ... lire, modifier, sauvegarder — au flush, une OptimisticLockException signifie qu'un autre a gagné la course
```

**Pourquoi c'est un piège :** les candidats récitent « l'optimiste est meilleur parce qu'il ne bloque pas » comme une
règle universelle — une réponse senior nomme le point de bascule : sous une contention réellement forte sur un
petit ensemble de lignes chaudes (voir S9), la tempête de retries du locking optimiste peut coûter plus cher que le blocage que
le locking pessimiste aurait causé, et le choix de l'un ou l'autre doit découler du pattern d'accès
réel, pas d'une préférence systématique.

#### Q17. Comment PostgreSQL peut-il lui-même servir de work queue avec `SELECT ... FOR UPDATE SKIP LOCKED`, et quelles en sont les limites ?
**Réponse :** Plusieurs workers qui interrogent une table `jobs` traiteraient normalement soit la même ligne
deux fois, soit se bloqueraient mutuellement sur les locks de lignes. `FOR UPDATE SKIP LOCKED` fait en sorte que la requête de chaque worker
prenne les premières lignes que *personne d'autre ne détient actuellement* et saute silencieusement celles verrouillées, de sorte que N workers
réclament des lots disjoints en concurrence sans service de coordination. La bonne forme est
**claim-then-process** : dans une transaction courte, sélectionner et marquer les lignes (`status = 'RUNNING'`, un
timestamp `locked_at`/lease, un id de worker), commit, faire le travail lent *en dehors* de toute transaction,
puis marquer comme terminé. Garder le lock de ligne ouvert pendant tout le job immobiliserait une connexion et une
transaction (bloquant vacuum, S19), ce n'est donc pas un substitut. Comme le claim est commité, un
worker qui plante laisse une ligne bloquée en `RUNNING` — il faut un **reaper** qui remet en file les lignes dont le
lease a expiré, ce qui signifie que les jobs s'exécutent *au moins une fois* et que les handlers doivent être idempotents (module 4
Q13). Autres limites : l'ordre n'est qu'approximatif sous concurrence, il n'y a ni backoff de retry intégré,
ni dead-letter ni fan-out, le polling ajoute de la latence et de la charge (à atténuer avec `LISTEN/NOTIFY`), et
le débit plafonne bien en dessous d'un vrai broker. C'est un excellent choix pour des volumes modestes où
l'on veut le job et ses données métier dans la *même transaction* (un outbox léger, module
4 Q26) et un mauvais choix comme bus d'événements généraliste.

**Exemple :**
```sql
-- Réclame jusqu'à 10 jobs atomiquement ; des workers concurrents ne reçoivent jamais la même ligne.
with next as (
    select id
    from jobs
    where status = 'PENDING' and run_at <= now()
    order by run_at, id
    limit 10
    for update skip locked
)
update jobs j
set status = 'RUNNING', locked_at = now(), attempts = attempts + 1
from next
where j.id = next.id
returning j.*;

-- Reaper (exécuté périodiquement) : rend les jobs dont le worker est mort.
update jobs set status = 'PENDING'
where status = 'RUNNING' and locked_at < now() - interval '10 minutes';
```

**Pourquoi c'est un piège :** les candidats soit l'écartent (« utilisez un broker »), soit lui font trop confiance. Les
points dignes d'un entretien sont la séparation claim/lease, le reaper, et la sémantique at-least-once qui en découle
— sans eux, la queue fonctionne en démo et se bloque ou traite en double après le
premier crash de worker.

### ORM & Hibernate

#### Q18. Qu'est-ce que le problème des requêtes N+1, et citez deux façons de le corriger.
**Réponse :** Récupérer une liste de N entités parentes, puis déclencher paresseusement une requête supplémentaire *par* parent
pour récupérer une collection associée (par ex. charger 50 commandes, puis déclencher 50 requêtes distinctes
pour récupérer les lignes de chaque commande) — 1 requête devient N+1, et cela croît linéairement avec la taille du result set
de la pire manière possible. Corrections : (1) un JOIN FETCH en JPQL (ou une jointure explicite en MyBatis/
JDBC) pour ramener l'association dans la même requête que le parent ; (2) `@EntityGraph` dans Spring Data
JPA pour déclarer quelles associations charger en eager pour une méthode de requête précise, sans changer
globalement le type de fetch par défaut de l'entité. Le batch fetching (`@BatchSize` / la config de batch fetch par défaut d'Hibernate)
est une troisième correction, plus grossière — elle n'élimine pas les requêtes supplémentaires mais les regroupe
en beaucoup moins d'aller-retours.

**Exemple :**
```java
// N+1 : une requête pour les commandes, puis une requête de plus par commande pour ses lignes.
List<Order> orders = orderRepository.findAll();
orders.forEach(o -> o.getItems().size()); // déclenche une requête de lazy-load, une fois par commande

// Correction 1 : JOIN FETCH ramène les lignes dans la même requête que le parent.
@Query("select o from Order o join fetch o.items")
List<Order> findAllWithItems();

// Correction 2 : @EntityGraph limite le fetch eager à cette seule méthode de requête.
@EntityGraph(attributePaths = "items")
List<Order> findAll();
```

**Pourquoi c'est un piège :** la « correction » tentante est de passer l'association en `FetchType.EAGER` sur
l'entité elle-même — cela résout cette requête-ci, mais désormais *toute* autre requête touchant cette entité
ramène aussi l'association en eager, et empiler deux collections eager sur la même entité produit
une jointure à produit cartésien qui peut être bien pire que le N+1 qu'elle remplaçait.

#### Q19. Nommez les quatre états d'une entité Hibernate, avec un exemple d'usage pour chacun.
**Réponse :** **Transient** : un simple `new Entity()`, non associé à aucun persistence context et non
représenté en base — `new Order()` avant `save()`. **Persistent** (managed) : attaché
à un persistence context actif ; ses changements sont automatiquement suivis et flushés vers la base
au commit/flush sans appel explicite à `save()` — une entité retournée par
`entityManager.find()` dans une session ouverte. **Detached** : était persistent, mais son persistence
context s'est fermé (par ex. la transaction s'est terminée, ou elle a été explicitement `.detach()`ée) — son
identité correspond toujours à une ligne en base, mais ses changements ne sont plus suivis ; la rattacher via
`merge()` est une source courante de bugs subtils si l'appelant ne réalise pas qu'une copie detached périmée
est fusionnée par-dessus des données plus récentes. **Removed** : marqué pour suppression dans le persistence
context courant via `entityManager.remove()`, supprimé de la base au flush/commit, mais l'objet Java
lui-même existe toujours en mémoire jusqu'à ce qu'il soit garbage-collecté.

**Exemple :**
```java
Order order = new Order();          // transient — non suivi, pas en base
em.persist(order);                  // persistent — désormais managed, dirty-check automatique
order.setStatus("SHIPPED");         // pas de save() explicite nécessaire — flushé au commit

em.close();                         // order est maintenant detached — les changements ne sont plus suivis
order.setStatus("CANCELLED");       // silencieusement non suivi ; rien ne se passe avant merge()
Order merged = em.merge(order);     // rattache — mais écrase la ligne en base avec les valeurs de champs
                                     // de cet objet, même si la ligne en base a changé depuis le detach

em.remove(merged);                  // removed — supprimé au flush/commit, l'objet existe toujours dans la JVM
```

**Pourquoi c'est un piège :** l'état que les candidats se trompent est **detached** — supposer que `merge()` « synchronise »
l'objet sans risque, alors qu'il écrase en réalité la ligne actuelle en base avec les valeurs de champs de l'objet detached
en bloc. Si une autre transaction a mis à jour cette ligne après le detach de cet objet,
`merge()` écarte silencieusement cette écriture plus récente sans détection de conflit, à moins que `@Version` (Q16)
ne soit aussi en jeu pour l'attraper.

#### Q20. Pourquoi les inserts/updates générés par l'ORM sont-ils souvent lents en masse, et comment y remédier ?
**Réponse :** Par défaut, la plupart des ORM émettent une instruction `INSERT`/`UPDATE` par entité, dans une boucle — pour un lot
de 10 000 lignes, cela fait 10 000 aller-retours (ou 10 000 instructions même en pipeline), chacune payant
un surcoût par instruction. Corrections : activer les paramètres de batch d'Hibernate
(`hibernate.jdbc.batch_size`, plus `order_inserts`/`order_updates` pour que les instructions d'une même table soient
regroupées afin que le batch s'applique réellement), ce qui fusionne plusieurs instructions en moins d'aller-retours
réseau via l'API de batch de JDBC ; ou contourner l'ORM pour les opérations réellement en masse et utiliser un
`INSERT ... VALUES (...), (...), (...)` natif multi-lignes ou la commande `COPY` de Postgres, qui est
considérablement plus rapide que même un insert ORM bien batché pour de gros volumes.

**Exemple :**
```properties
# Activer batch_size seul ne suffit pas :
hibernate.jdbc.batch_size=50
# Sans ceux-ci, des types d'entités entrelacés dans le persistence context cassent les batches :
hibernate.order_inserts=true
hibernate.order_updates=true
```
```sql
-- Chemin le plus rapide pour des chargements réellement en masse, en contournant totalement l'ORM :
copy orders (id, customer_id, status) from stdin with (format csv);
```

**Pourquoi c'est un piège :** régler `hibernate.jdbc.batch_size` seul et croire que c'est toute la correction —
sans `order_inserts`/`order_updates`, Hibernate ne fusionne toujours pas les instructions si
des types d'entités différents sont entrelacés dans le persistence context (par ex. sauvegarder un `Order`, puis un
`Payment`, puis un autre `Order`), donc l'insert « batché » revient silencieusement à des instructions une par une
en l'absence du flag manquant.

#### Q21. En quoi l'approche de persistance de MyBatis diffère-t-elle de celle de JPA/Hibernate, et quand cette différence est-elle le facteur décisif ?
**Réponse :** JPA/Hibernate est un ORM complet : on déclare des mappings d'entités et on laisse Hibernate générer le SQL, gérer
un persistence context avec dirty-checking, et prendre en charge le caching/lazy-loading de façon transparente — ce qui
est puissant mais signifie que le SQL réellement exécuté est un peu indirect et peut vous surprendre (N+1,
jointures inattendues). MyBatis est un SQL mapper, pas un ORM complet : vous écrivez le SQL (ou un template assez léger
basé sur XML/annotations) explicitement, et le rôle de MyBatis est uniquement de binder les paramètres
en entrée et de mapper les colonnes du résultat vers des objets — il n'y a ni persistence context, ni
dirty-checking automatique, ni requêtes cachées. Le facteur décisif en pratique : recourir à MyBatis quand
les requêtes sont complexes, nécessitent un tuning spécifique à la base, ou quand une équipe veut explicitement voir et
contrôler chaque instruction SQL exécutée (courant dans les environnements sensibles à la performance ou à schéma
legacy où le SQL généré par l'ORM serait un handicap, pas une commodité).

**Exemple :**
```java
// JPA : le SQL réel est généré par Hibernate — le dirty-checking est gratuit.
Order order = em.find(Order.class, id);
order.setStatus("SHIPPED"); // aucune instruction update écrite nulle part — flushé au commit

// MyBatis : le SQL est explicite et visible ; pas de dirty-checking caché ni de cache de session.
@Update("update orders set status = #{status} where id = #{id}")
void updateStatus(@Param("id") Long id, @Param("status") String status);
```

**Pourquoi c'est un piège :** « MyBatis n'a pas de surcoût d'ORM donc il est toujours plus rapide » simplifie à l'excès la
comparaison — une grande partie de ce qu'un persistence context JPA offre gratuitement (dirty-checking, éviter une
requête en double pour une entité déjà chargée dans cette transaction) est du travail qu'une base de code MyBatis
doit réécrire à la main si le cas d'usage l'exige vraiment. Le bon choix dépend du niveau de
contrôle sur le SQL exact dont l'équipe a besoin, pas d'un verdict de performance systématique.

### Connexions & topologie

#### Q22. Comment dimensionnez-vous un pool de connexions HikariCP, et quelle est l'erreur de dimensionnement courante ?
**Réponse :** L'erreur courante est de dimensionner le pool bien plus grand que nécessaire, par intuition que « plus de
connexions = plus de débit » — en réalité, au-delà d'un certain point (à peu près lié au nombre de cœurs CPU du serveur
de base de données et à sa capacité à faire du context-switch entre requêtes actives), ajouter
des connexions ajoute de la contention côté base et *réduit* le débit au lieu de l'augmenter.
Le guide de HikariCP lui-même, basé sur la formule du wiki PostgreSQL, est à peu près
`connections = ((core_count * 2) + effective_spindle_count)` comme point de départ pour le budget de connexions
*total du serveur de base de données*, divisé entre toutes les instances applicatives qui
le partagent — pas par instance. La règle pratique : commencer plus petit que ce que l'intuition suggère, faire des load tests
pour trouver la taille de pool qui maximise réellement le débit, et se rappeler que le pool de chaque instance applicative
se dispute le même budget de connexions côté base.

**Exemple :**
```yaml
# La « correction » réflexe face à une plainte de timeout — aggrave souvent les choses au lieu de les améliorer :
spring.datasource.hikari.maximum-pool-size: 200  # sur une base à 8 cœurs

# Point de départ bien dimensionné par instance, dérivé du nombre réel de cœurs de la base
# et divisé par le nombre d'instances partageant cette base :
spring.datasource.hikari.maximum-pool-size: 10
```

**Pourquoi c'est un piège :** « il suffit d'augmenter `maximum-pool-size` » est la correction réflexe de toute
plainte de requête lente sous charge — au-delà du vrai point optimal de concurrence de la base, ajouter des
connexions ajoute du context-switching et de la contention de locks sur le serveur, rendant la latence *pire* et non
meilleure, ce qui est le contraire de l'objectif du changement.

#### Q23. Comment configurez-vous et routez-vous en toute sécurité vers plusieurs data sources dans une même application Spring ?
**Réponse :** Définir chaque `DataSource` comme son propre `@Bean`, marquer celle par défaut `@Primary`, lier chacune à son
propre préfixe de configuration, et — de façon critique pour la correction, pas seulement pour le câblage — configurer des beans
`EntityManagerFactory`/`TransactionManager` séparés par data source si ce sont des bases réellement
indépendantes, car une seule frontière `@Transactional` ne peut pas couvrir atomiquement deux bases
physiquement séparées (pas de 2-phase-commit distribué par défaut). Le piège senior ici est de
supposer que `@Transactional` donne l'atomicité sur les deux data sources comme il le fait au sein d'une seule —
ce n'est pas le cas, à moins qu'un gestionnaire de transactions distribué (JTA/XA) soit explicitement configuré, ce que
la plupart des équipes évitent à cause de son coût opérationnel, préférant concevoir autour de la contrainte (par ex. une seule
data source est toujours la « source de vérité » pour une écriture donnée).

**Exemple :**
```java
@Bean @Primary
DataSource ordersDataSource() { return DataSourceBuilder.create().build(); }

@Bean
DataSource billingDataSource() { return DataSourceBuilder.create().build(); }

@Transactional // cette frontière ne couvre que le travail d'UNE SEULE des deux data sources à la fois
void processOrder() {
    ordersRepository.save(order);      // commité via le transaction manager de ordersDataSource
    billingRepository.save(invoice);   // une transaction SÉPARÉE, commitée indépendamment —
                                        // si celle-ci lève une exception, la commande ci-dessus n'est pas annulée (rollback)
}
```

**Pourquoi c'est un piège :** supposer que `@Transactional` donne une atomicité inter-bases de la même façon qu'au
sein d'une seule data source — sans gestionnaire de transactions JTA/XA explicite, un échec sur la
seconde écriture laisse la première commitée, et aucune annotation dans ce code ne corrige cela silencieusement ; la
solution est une décision de conception (retries idempotents, une saga, ou une source de vérité unique), pas
un flag de configuration manquant.

#### Q24. Qu'est-ce qui casse quand on ajoute naïvement un read replica pour scaler les lectures ?
**Réponse :** Le mode d'échec évident : l'**incohérence read-after-write** — un client écrit sur le primary,
puis lit immédiatement depuis un replica qui n'a pas encore reçu (ou appliqué) cette écriture à cause du
retard de réplication, et voit des données périmées, ce qui est particulièrement déroutant pour un utilisateur qui vient de soumettre
un formulaire et recharge pour voir que son propre changement est absent. Cela se manifeste notamment dans des flux comme
« créer une ressource, puis rediriger vers sa page de détail » si la lecture du détail est routée vers un
replica en retard. Corrections : router les lectures qui doivent être immédiatement cohérentes avec une écriture qui vient de se terminer vers
le primary (ou vers le même replica auquel la session d'écriture est épinglée), accepter et concevoir
autour de la cohérence à terme pour les lectures qui la tolèrent, ou surveiller le retard de réplication et
router les lectures loin d'un replica qui a pris trop de retard.

**Exemple :**
```java
Long orderId = orderService.create(request);  // l'écriture va vers le primary
return "redirect:/orders/" + orderId;

// Le GET redirigé, s'il est routé vers un replica en retard :
Order order = orderRepository.findById(orderId); // 404 ou périmé — le replica n'a pas encore rattrapé
```

**Pourquoi c'est un piège :** « ajouter un read replica » est traité comme un gain de scaling sans aucun inconvénient
de cohérence — le premier incident de production dû à cela est presque toujours exactement le flux
create-then-redirect ci-dessus, découvert par un utilisateur perplexe plutôt qu'attrapé en revue.

### Schéma & modélisation

#### Q25. Quel est le processus sûr pour une migration de schéma sur une base de production, et quels outils la gèrent ?
**Réponse :** Flyway et Liquibase sont les outils standards — chaque migration est un script versionné et suivi
(SQL ou, pour Liquibase, aussi XML/YAML) appliqué dans l'ordre et enregistré dans une table d'historique des migrations,
de sorte que l'état courant du schéma est toujours déductible et reproductible d'un environnement à l'autre. Le
processus sûr pour un changement de forme cassante (renommer une colonne, ajouter une contrainte `NOT NULL`)
consiste à le découper en plusieurs étapes déployables et rétrocompatibles plutôt qu'en une seule migration :
ajouter la nouvelle colonne nullable, déployer le code applicatif qui écrit à la fois dans l'ancienne et la nouvelle, remplir (backfill) les
lignes existantes, déployer le code qui ne lit que la nouvelle colonne, puis supprimer l'ancienne colonne dans une
dernière migration — à chaque étape intermédiaire, l'ancienne comme la nouvelle version de l'application peuvent tourner
sur le schéma courant, ce qui rend possible un déploiement rolling sans interruption.

**Exemple :**
```sql
-- V1 : additif, sûr sur une table en production quelle que soit la version de Postgres
alter table users add column email_normalized text;

-- Déploiement applicatif : écrit email_normalized à chaque écriture, les lectures utilisent encore l'ancienne colonne.

-- V2 : backfill par lots (voir Q20/S12), pas un seul UPDATE géant.
-- Déploiement applicatif : les lectures basculent vers email_normalized.

-- V3, une fois la bascule complète :
alter table users drop column email;
```

**Pourquoi c'est un piège :** la migration unique « évidente » — ajouter directement la colonne `NOT NULL` en une
étape — passe souvent sans problème sur une petite base de staging à faible charge, puis verrouille ou échoue
en production simplement parce que la production a des ordres de grandeur de lignes en plus et un trafic concurrent
que le staging n'a jamais eu ; le pattern en plusieurs étapes n'est pas une précaution excessive, c'est la seule version qui
passe à l'échelle réelle et à la concurrence de la production.

#### Q26. Quand une colonne doit-elle être `JSONB` plutôt qu'un ensemble de tables correctement normalisées ?
**Réponse :** `JSONB` convient aux données réellement semi-structurées, éparses ou à schéma variable — un
sac d'« attributs personnalisés » sur un produit qui varie fortement selon la catégorie, ou le payload d'un journal d'audit
qui n'est pas interrogé structurellement, seulement stocké et occasionnellement récupéré en entier. Il est mal adapté
aux données à structure stable et bien connue, fréquemment interrogées, filtrées, jointes ou
agrégées par champs individuels — à ce stade, les colonnes normalisées sont à la fois plus rapides (un vrai
B-tree sur une vraie colonne bat même une recherche de clé JSONB indexée par GIN pour la plupart des patterns d'accès) et
offrent une vraie intégrité référentielle (clés étrangères, `NOT NULL`, contraintes `CHECK`) que JSONB
ne peut pas imposer au niveau de la base. Le piège à surveiller en revue : recourir à JSONB parce que
c'est commode en début de développement, puis l'avoir encore un an plus tard dans un chemin chaud, fréquemment filtré,
avec un index GIN qui cache ce qui aurait dû être une colonne normalisée dès
le départ.

**Exemple :**
```sql
-- Correct : réellement épars, à schéma variable, rarement filtré structurellement.
create table products (
    id bigint primary key,
    custom_attributes jsonb -- varie fortement selon la catégorie, surtout stocké/récupéré en entier
);

-- Mal adapté : structure stable, filtré/joint en permanence — devrait être de vraies colonnes.
select * from orders where payload @> '{"status": "SHIPPED", "region": "EU"}'; -- vs :
select * from orders where status = 'SHIPPED' and region = 'EU'; -- normalisé, indexable, contraint
```

**Pourquoi c'est un piège :** recourir à `JSONB` parce que c'est commode en début de développement, et
ne jamais revoir cette décision une fois que le champ devient une colonne stable et fréquemment filtrée, c'est
ainsi qu'un index GIN finit par cacher ce qui aurait dû être une colonne normalisée avec une vraie
clé étrangère et une contrainte `NOT NULL` dès le départ.

#### Q27. Soft deletes vs hard deletes — quel est le vrai compromis ?
**Réponse :** Les soft deletes (un timestamp `deleted_at` ou un flag `is_deleted`, les lignes n'étant jamais physiquement supprimées)
préservent l'historique d'audit, permettent l'« annulation » et évitent les surprises de cascade de clés étrangères (voir S15) —
mais chaque requête de la base de code doit désormais penser à filtrer les lignes soft-deleted
(facile à oublier, ce qui fait resurgir une ligne soft-deleted dans les résultats), les contraintes d'unicité se
compliquent (une nouvelle ligne peut-elle réutiliser un email qu'une ligne soft-deleted détient encore ?), et la table
grossit sans limite puisque rien n'est jamais réellement supprimé. Les hard deletes gardent la table et ses
contraintes simples et imposent une vraie récupération d'espace, au prix de la perte de l'historique et du besoin d'un
mécanisme d'audit/archivage séparé si cet historique est réellement requis pour la conformité ou le
support. De nombreux systèmes de production aboutissent à un hybride : soft delete pendant une fenêtre de rétention (permet
l'annulation et l'audit des changements récents), suivi d'un job planifié qui hard-delete les lignes au-delà de cette
fenêtre.

**Exemple :**
```sql
-- Filtre oublié : un utilisateur soft-deleted resurgit dans les résultats.
select * from users where email = 'ann@example.com'; -- retourne aussi la ligne « supprimée »

-- Une contrainte d'unicité simple empêche une nouvelle inscription de réutiliser cet email :
alter table users add constraint uq_users_email unique (email); -- détient encore l'email de la ligne supprimée

-- La vraie correction pour les deux : filtrer explicitement les lignes supprimées, et limiter l'unicité aux lignes actives.
create unique index uq_users_email_active on users(email) where deleted_at is null;
```

**Pourquoi c'est un piège :** le soft delete est souvent supposé être le défaut strictement « plus sûr » — mais il
échange une classe de bug qu'un hard delete ne peut structurellement pas avoir (oublier le filtre `deleted_at is null`
et refaire fuiter des données supprimées dans une requête) contre le bénéfice d'audit/annulation, et une contrainte
d'unicité naïve sur une colonne email bloquera silencieusement une réinscription légitime à moins d'être explicitement
limitée aux lignes non supprimées.

## 🔴 Expert / Ouvert

### Conception de schéma & d'indexation

#### Q28. `bigint` auto-incrémenté, UUID aléatoire (v4) ou UUID ordonné dans le temps (v7) pour les clés primaires — comment choisir ?
Chaque option optimise quelque chose de différent. Un **`bigint` identity/sequence** est petit (8 octets),
l'index est dense et les inserts vont toujours vers la page B-tree la plus à droite (excellente localité et comportement
de cache), et les jointures sont rapides ; les inconvénients sont que les ids sont devinables (attaques par énumération
si l'autorisation n'est pas correcte, module 2 Q36), ils révèlent le volume (« nous avons 4 231 commandes »),
ils nécessitent une séquence centrale, et la fusion de données de plusieurs bases provoque des collisions. Un **UUIDv4 aléatoire**
peut être généré n'importe où sans coordination et n'est pas devinable, mais il fait 16 octets et est
*uniformément aléatoire*, donc chaque insert atterrit sur une page feuille aléatoire de l'index de clé primaire : splits
de pages, un working set bien plus grand qui ne tient plus en cache, amplification d'écriture (full-page images du
WAL), et un débit d'insert et une taille d'index nettement pires à des centaines de millions
de lignes. Un **UUIDv7** conserve la propriété d'unicité globale sur 16 octets mais place un timestamp en millisecondes
dans les bits de poids fort, donc les nouvelles clés sont à peu près croissantes — une localité d'insert similaire à une séquence —
tout en restant adapté au distribué (PostgreSQL 18 fournit un `uuidv7()` intégré ; les versions antérieures
nécessitent une extension ou le génèrent dans l'application). Deux considérations supplémentaires : le timestamp
dans une clé v7 révèle l'*heure de création*, et les index secondaires ainsi que chaque colonne de clé étrangère répètent la
clé, donc 16 contre 8 octets se multiplie à travers le schéma. Avec Hibernate, utiliser un
générateur `SEQUENCE` avec `allocationSize` correspondant à l'incrément de la base (la stratégie `IDENTITY`
désactive le batching d'inserts JDBC, Q20). Ma recommandation par défaut : une clé primaire interne `bigint`
pour les jointures plus, si des identifiants visibles de l'extérieur sont requis, un id public aléatoire séparé (ou
UUIDv7 comme clé primaire quand les ids sont générés dans de nombreux services ou clients) ; éviter v4 comme chemin chaud d'insert
clustered sur de grandes tables, et décider une fois pour toutes — changer plus tard le type de clé primaire est
l'une des migrations les plus coûteuses qui soient.

#### Q29. Concevez le schéma et la stratégie d'indexation d'une table de feed/événements à forte écriture, en append, censée atteindre des milliards de lignes.
**Réponse :** Privilégier un pattern d'insert en append-only (éviter les updates autant que possible — les updates sur une énorme table
luttent avec vacuum et le bloat, voir S14) et partitionner la table par temps (partitionnement par plage natif PostgreSQL
sur une colonne timestamp) pour que les requêtes limitées à une fenêtre de temps récente ne touchent que
les partitions récentes, et que les anciennes partitions puissent être supprimées en bloc (instantané, contrairement à un `DELETE` lent
parcourant des milliards de lignes) dès qu'une politique de rétention les fait expirer. Indexer de façon délibérée et parcimonieuse
— chaque index supplémentaire ajoute un coût d'écriture à chaque insert, ce qui compte énormément à ce volume
d'écriture — typiquement juste les colonnes réellement utilisées pour filtrer les feeds (`user_id`, `created_at`)
plutôt que chaque colonne susceptible d'être interrogée en théorie. Se demander si le pattern de lecture
a vraiment besoin de la flexibilité de requêtage relationnelle, ou si un store time-series ou
wide-column dédié est mieux adapté une fois que le surcoût d'indexation relationnelle devient le goulot d'étranglement — la
réponse de niveau senior reconnaît que « continuer à scaler Postgres » et « le modèle de données ne convient plus à une base
relationnelle sous cette forme » sont deux réponses légitimes selon les patterns de requête réels, pas seulement
le nombre de lignes.

**Exemple :**
```sql
create table events (
    id bigint generated always as identity,
    user_id bigint not null,
    created_at timestamptz not null,
    payload jsonb
) partition by range (created_at);

create table events_2026_01 partition of events
    for values from ('2026-01-01') to ('2026-02-01');

create index on events (user_id, created_at); -- uniquement les colonnes par lesquelles les feeds sont réellement filtrés

-- Rétention : instantanée, contrairement à un DELETE qui parcourrait des milliards de lignes.
drop table events_2025_01;
```

**Pourquoi c'est un piège :** sur-indexer « par sécurité » une table à ce volume d'écriture est une vraie
erreur, pas de la prudence — chaque index supplémentaire est une amplification d'écriture payée à chaque insert,
et à des milliards de lignes, des index qui n'ont jamais été utilisés par un vrai pattern de requête sont du pur
coût sans aucun bénéfice compensatoire.

#### Q30. Concevez l'indexation d'un écran de recherche qui filtre les commandes par statut et date, retrouve les clients par e-mail sans tenir compte de la casse, et supporte la recherche textuelle « contient ». Quelles fonctionnalités d'index utilisez-vous ?
C'est une question de boîte à outils : associer chaque forme de requête au plus petit index qui la sert, puisque chaque
index coûte du débit d'écriture, du disque et du travail de vacuum. (1) **B-tree composite** pour la liste
principale — colonnes d'égalité d'abord, colonne de plage/tri en dernier (Q13) : `(customer_id, status, created_at desc)`.
(2) **Index partiel** quand les requêtes touchent un petit sous-ensemble chaud : si 95 % des lignes sont `DELIVERED` mais que
l'écran lit `PENDING`, `create index on orders (created_at) where status = 'PENDING'` est minuscule,
peu coûteux à maintenir et exactement aussi sélectif que nécessaire ; le `WHERE` de la requête doit impliquer le prédicat
de l'index. (3) Un **index couvrant** avec `INCLUDE (total, customer_name)` permet à PostgreSQL de répondre
depuis l'index seul — un *index-only scan* — en évitant les accès au heap ; cela ne fonctionne que si la
visibility map est à jour (vacuum régulier) et chaque colonne incluse supplémentaire élargit l'index. (4)
**Index d'expression** pour les fonctions : `where lower(email) = lower(:e)` ne peut pas utiliser un index simple sur
`email` ; `create index on customers (lower(email))` (ou le type `citext`) le peut, et la requête doit
utiliser la *même expression*. (5) **`LIKE '%term%'`** et `ILIKE` ne peuvent pas du tout utiliser un B-tree (pas de
préfixe fixe), donc une recherche avec joker en tête scanne la table ; la solution est un **index trigram GIN/GiST**
(`pg_trgm`, `create index ... using gin (name gin_trgm_ops)`), ou une vraie recherche plein texte
(`tsvector` + GIN) s'il s'agit d'une recherche linguistique, ou un moteur de recherche externe quand la pertinence, les facettes
et la tolérance aux fautes de frappe comptent. (6) Toujours construire sur une table en production avec `CREATE INDEX CONCURRENTLY` (il
prend plus de temps et ne peut pas s'exécuter dans une transaction, et une exécution échouée laisse un index `INVALID` à supprimer),
et supprimer périodiquement les index que `pg_stat_user_indexes.idx_scan` montre comme jamais utilisés —
chacun ralentit toujours chaque `INSERT`/`UPDATE`, et un update qui touche une colonne indexée
perd le chemin économique de HOT-update de PostgreSQL. Prouver chaque choix avec `EXPLAIN (ANALYZE, BUFFERS)` (Q14)
sur des données à l'échelle de la production plutôt qu'à l'intuition.

#### Q31. Quand le partitionnement de table est-il la bonne réponse dans PostgreSQL, et que vous coûte-t-il ?
Le partitionnement déclaratif (`PARTITION BY RANGE (created_at)`, ou `LIST`/`HASH`) découpe une
table logique en tables filles physiques. Il est rentable dans trois situations : la **rétention** (supprimer
ou détacher une ancienne partition est une opération de métadonnées instantanée, alors que `DELETE`-er 200 millions
d'anciennes lignes génère la même quantité de WAL, de dead tuples et de travail de vacuum — la table en append de
la Q29 est le cas d'école), le **partition pruning** (une requête avec un filtre sur la clé de partition ne
touche que les partitions pertinentes, donc « les 7 derniers jours » scanne une ou deux filles au lieu d'un
index de plusieurs années), et la **granularité de maintenance** (vacuum, reindex et sauvegardes s'exécutent par partition
plutôt que sur un objet de 2 To). Les coûts sont réels et expliquent pourquoi ce n'est pas la première chose à
essayer. Le pruning n'a lieu que quand la requête *filtre sur la clé de partition* — une requête sans
prédicat sur `created_at` scanne toutes les partitions et est plus lente qu'avant. Chaque clé primaire ou
contrainte d'unicité doit **inclure la clé de partition**, donc il n'y a pas d'unicité globale bon marché sur
`id` seul. Trop de partitions (des milliers) ralentissent le planning et consomment de la mémoire, donc choisir une
granularité qui donne de quelques dizaines à quelques centaines — journalière pour un très gros volume, mensuelle sinon.
Les partitions doivent être créées *à l'avance* (un job ou `pg_partman`), sinon les inserts échouent le jour où
personne n'a créé celle du mois suivant — toujours garder une partition `DEFAULT` ou une alerte dessus. Les clés étrangères
*vers* une table partitionnée ont des restrictions, et les changements de schéma doivent être appliqués de façon cohérente à
toutes les filles. Ma règle de décision : ne pas partitionner tant que la table n'est pas assez grande pour que vacuum,
la taille des index ou les deletes de rétention fassent réellement mal (souvent des centaines de millions de lignes ou des centaines de
Go), et que les requêtes dominantes filtrent déjà sur le temps ; avant cela, un bon index composite/partiel
(Q30) et l'archivage sont plus simples. Si la rétention est la *seule* raison, le
`DROP PARTITION` d'une table partitionnée est l'argument le plus fort. Tester avec `EXPLAIN` que le pruning a réellement lieu
(`Subplans Removed`/seules les partitions pertinentes listées) et surveiller le nombre de lignes par partition pour repérer le skew.

### Évolution & compromis

#### Q32. Comment ajoutez-vous en toute sécurité une colonne `NOT NULL` à une table de 50 millions de lignes sans aucune interruption ?
**Réponse :** Ne jamais ajouter `NOT NULL` directement dans une seule migration sur une énorme table sous charge d'écriture concurrente — dans
les anciennes versions de Postgres, cela réécrivait toute la table sous un lock exclusif ; même avec les
améliorations du Postgres moderne (ajouter une colonne avec un défaut constant ne réécrit plus la
table), ajouter `NOT NULL` exige toujours de valider chaque ligne existante, ce qui verrouille brièvement la
table si c'est fait en une seule étape bloquante. Séquence sûre : (1) ajouter la colonne nullable ; (2) backfill
des lignes existantes par petits lots (pour éviter une seule transaction géante de longue durée et pour ne pas
submerger la réplication/vacuum), l'application continuant de fonctionner puisque la colonne
autorise `NULL` ; (3) ajouter la contrainte `NOT NULL` avec `NOT VALID` plus une étape séparée `VALIDATE
CONSTRAINT` (spécifique à Postgres : `NOT VALID` ajoute la contrainte instantanément sans
valider les lignes existantes, puis `VALIDATE CONSTRAINT` les vérifie avec un lock bien plus léger,
en concurrence avec les opérations normales) ; (4) déployer le code applicatif qui écrit toujours une valeur
pour la nouvelle colonne, calé pour que cela ait lieu avant que la contrainte soit appliquée. Le pattern
se généralise : tout changement de schéma sur une énorme table en production est scindé en une étape nullable/permissive, un
backfill, et une étape d'application stricte, chacune déployable indépendamment et sûre à exécuter
sans bloquer le trafic concurrent.

**Exemple :**
```sql
-- Étape 1 : instantanée, sans réécriture de table.
alter table orders add column region text;

-- Étape 2 : backfill par lots, pas une seule transaction géante (voir S12).
update orders set region = 'UNKNOWN' where id between 1 and 10000 and region is null;
-- ... répéter par tranches ...

-- Étape 3 : ajout instantané de la contrainte, sans validation pour l'instant — puis validation avec un lock plus léger.
alter table orders add constraint orders_region_not_null check (region is not null) not valid;
alter table orders validate constraint orders_region_not_null;
```

**Pourquoi c'est un piège :** la migration qui « marche simplement » dans un environnement de staging avec quelques milliers de
lignes et sans trafic concurrent est exactement celle qui verrouille la production pendant toute la durée d'une
validation de table complète — la différence n'apparaît qu'à l'échelle réelle de la production, ce qui est
précisément pourquoi cela doit être un pattern délibéré et testé plutôt que quelque chose découvert à la
dure pendant un déploiement.

#### Q33. Quand dénormalisez-vous délibérément, et comment maintenez-vous la cohérence de la copie dénormalisée ?
**Réponse :** Dénormaliser quand un pattern de lecture est à la fois extrêmement chaud et coûteux à calculer à partir de données
normalisées à chaque requête — un total cumulé, un agrégat fréquemment affiché (nombre de commentaires sur un
post, nombre d'abonnés sur un profil), ou des données jointes si souvent que le coût de la jointure lui-même est le
goulot d'étranglement. Le compromis est explicite : on accepte une charge de maintenance de la cohérence en
échange de la vitesse de lecture, et cette charge exige un mécanisme délibéré, pas « penser à
le mettre à jour partout » — les options incluent la mise à jour de la valeur dénormalisée de façon transactionnelle
avec l'écriture de la source de vérité (même transaction, donc elle ne peut jamais dériver, mais cela couple les
deux écritures), une mise à jour asynchrone pilotée par événements/queue (cohérente à terme, découplée, mais nécessite une
surveillance de la dérive et un job de réconciliation pour rattraper les événements manqués), ou une vue matérialisée
rafraîchie selon un planning (simple, mais aussi fraîche que le dernier rafraîchissement). La réponse digne d'un entretien
nomme le mécanisme précis choisi et son mode d'échec précis — « je le mettrais en cache » sans
dire comment l'obsolescence ou la dérive est détectée et corrigée est une réponse incomplète au niveau senior.

**Exemple :**
```sql
-- Compteur dénormalisé, mis à jour dans la même transaction que l'écriture de la source de vérité :
begin;
insert into comments (post_id, body) values (42, 'nice post');
update posts set comment_count = comment_count + 1 where id = 42;
commit; -- ne peut jamais dériver — les deux écritures réussissent ou échouent ensemble

-- Un job de réconciliation pour rattraper la dérive d'une valeur dénormalisée mise à jour en asynchrone :
select p.id, p.comment_count, c.actual
from posts p
join (select post_id, count(*) actual from comments group by post_id) c on c.post_id = p.id
where p.comment_count <> c.actual; -- signale toute ligne qui a dérivé de la source de vérité
```

**Pourquoi c'est un piège :** « je le mettrais simplement en cache » ressemble à une réponse mais ne survit pas à la
question de suivi évidente — que se passe-t-il quand un événement de mise à jour est manqué, et comment quelqu'un s'en apercevrait-il ? Nommer
le mécanisme de réconciliation d'emblée est ce qui distingue une réponse senior d'une réponse plausible
qui n'a pas été testée face à un vrai mode d'échec.

## 🎯 Scénarios réels

### S1. Une requête qui était rapide devient de plus en plus lente à mesure que la table grossit
- **Symptômes :** La latence d'une requête précise a augmenté sur plusieurs mois proportionnellement à la croissance
  de la table, bien au-delà de ce que la seule croissance du nombre de lignes devrait provoquer.
- **Diagnostic :** Exécuter `EXPLAIN ANALYZE` (Q14) et vérifier la présence d'un `Seq Scan` là où un `Index Scan`
  serait attendu, ou un grand écart entre les nombres de lignes estimés et réels du planner
  (statistiques obsolètes).
- **Exemple :**
  ```
  Seq Scan on orders (actual time=0.02..812.40 rows=1200000 loops=1)
    Filter: (status = 'PENDING')
  Planning Time: 0.10 ms
  Execution Time: 815.02 ms
  ```
  Aucun index n'existe sur `status`, donc chaque requête qui filtre dessus scanne toute la table — et ce
  scan devient linéairement plus lent à mesure que la table grossit.
- **Résolution :** Ajouter l'index manquant (en vérifiant l'ordre des colonnes pour les cas composites, Q13), ou exécuter
  `ANALYZE` pour rafraîchir les statistiques si le plan est simplement faux à cause de statistiques obsolètes, ou
  réécrire la requête si une fonction enveloppant la colonne filtrée empêche l'usage de l'index.
- **Prévention :** Mettre en place une revue des requêtes basée sur `EXPLAIN` pour les nouvelles requêtes de chemin chaud avant leur livraison,
  et surveiller les slow-query logs en continu plutôt que de découvrir la dégradation via les retours utilisateurs.

### S2. Un outil d'APM signale des dizaines de requêtes quasi identiques déclenchées pour un seul chargement de page
- **Symptômes :** Une page qui liste 50 éléments déclenche 51+ requêtes en base — une pour la liste, et
  une par élément pour une collection associée.
- **Diagnostic :** N+1 classique (Q18) — le confirmer en vérifiant le type de fetch de l'association de l'entité et
  si le code itère sur la collection et accède à une association lazy dans la boucle.
- **Exemple :**
  ```
  select * from orders limit 50
  select * from line_items where order_id = 1
  select * from line_items where order_id = 2
  -- ... 48 autres, une par commande de la page
  ```
- **Résolution :** Ajouter un `JOIN FETCH` / `@EntityGraph` pour ce chemin de requête précis, ou configurer
  le batch fetching si un eager-join partout n'est pas approprié.
- **Prévention :** Ajouter une assertion sur le nombre de requêtes dans les tests d'intégration des endpoints d'affichage de listes
  (de nombreux frameworks de test permettent d'asserter un nombre maximal de requêtes par test) afin qu'une régression fasse échouer
  la CI au lieu d'être livrée.

### S3. Deux transactions concurrentes se bloquent mutuellement (deadlock), et l'une est annulée par la base
- **Symptômes :** Postgres journalise une erreur `deadlock detected`, nommant les deux processus en conflit
  et les locks que chacun détenait en attendant l'autre ; une transaction est automatiquement annulée (rollback)
  pour briser le cycle.
- **Diagnostic :** Le message de log nomme lui-même les requêtes exactes et les types de locks impliqués — la
  cause habituelle est deux transactions qui mettent à jour les deux mêmes lignes (ou tables) dans un ordre opposé (A
  puis B dans une transaction, B puis A dans une autre).
- **Exemple :**
  ```
  ERROR: deadlock detected
  DETAIL: Process 1234 waits for ShareLock on transaction 5678; blocked by process 5678.
          Process 5678 waits for ShareLock on transaction 1234; blocked by process 1234.
  Process 1234: UPDATE accounts SET balance = balance - 100 WHERE id = 2;
  Process 5678: UPDATE accounts SET balance = balance - 50  WHERE id = 1;
  ```
  La transaction 1234 a mis à jour `id = 1` puis voulait `id = 2` ; la transaction 5678 a d'abord mis à jour `id = 2`
  puis voulait `id = 1` — une acquisition de locks en ordre opposé classique.
- **Résolution :** Standardiser un ordre cohérent de lock/update dans tous les chemins de code qui touchent
  les deux ressources (toujours mettre à jour dans le même ordre, par ex. par clé primaire croissante), ou réduire la portée des
  transactions pour que les locks soient détenus moins longtemps, réduisant la fenêtre de conflit.
- **Prévention :** Gérer l'exception de deadlock avec un retry (la transaction annulée peut être rejouée sans risque —
  rien n'a été commité), et documenter l'ordre de lock requis pour toute opération multi-lignes
  réellement sujette à ce pattern.

### S4. Les requêtes échouent avec l'erreur « too many connections » propre à la base, indépendamment de la taille du pool côté application
- **Symptômes :** Le pool HikariCP de l'application n'est pas épuisé (les métriques montrent de la marge), mais la
  base elle-même rejette les nouvelles connexions.
- **Diagnostic :** Comparer le `max_connections` du serveur de base à la *somme* de la taille de pool de chaque
  instance applicative, plus tous les autres clients (outils d'admin, autres services partageant
  la base) — une flotte d'instances chacune généreusement dimensionnée peut collectivement dépasser la
  limite réelle du serveur même si le pool d'aucune instance ne paraît saturé.
- **Exemple :**
  ```
  FATAL: sorry, too many clients already
  ```
  ```
  show max_connections; -- 100
  -- 12 instances applicatives x maximum-pool-size: 15 chacune = 180 connexions possibles,
  -- déjà au-dessus de la limite du serveur avant même qu'un outil d'admin ne se connecte.
  ```
- **Résolution :** Réduire la taille de pool par instance en suivant les conseils de dimensionnement de la Q22, ou introduire un
  connection pooler (PgBouncer) devant la base pour multiplexer de nombreuses connexions applicatives sur moins de
  connexions réelles vers la base.
- **Prévention :** Suivre le total des connexions sur toute la flotte comme métrique de premier ordre par rapport à la
  limite configurée de la base, pas seulement l'utilisation du pool par instance.

### S5. Une migration de schéma verrouille une table de production et provoque une brève interruption
- **Symptômes :** L'étape de migration d'un déploiement provoque un pic de latence des requêtes ou des timeouts francs
  pendant toute la durée de la migration, sur une table soumise à un trafic actif de lecture/écriture.
- **Diagnostic :** Identifier l'instruction de migration précise — ajout d'une colonne avec un défaut non constant
  (avant les versions récentes de Postgres, cela réécrivait toute la table sous un lock exclusif),
  ajout d'une clé étrangère sans `NOT VALID` (valide toutes les lignes existantes sous lock), ou création
  d'un index sans `CONCURRENTLY` (bloque les écritures pendant toute la construction).
- **Exemple :**
  ```sql
  -- Bloque les écritures sur `orders` pendant toute la durée de construction de l'index :
  create index idx_orders_email on orders(customer_email);

  -- Équivalent non bloquant :
  create index concurrently idx_orders_email on orders(customer_email);
  ```
- **Résolution :** Réécrire la migration avec les équivalents non bloquants : `NOT VALID` +
  `VALIDATE CONSTRAINT` séparé pour les contraintes, `CREATE INDEX CONCURRENTLY` pour les index, et
  le pattern en plusieurs étapes de la Q32 pour tout ce qui exigerait autrement une réécriture ou un scan complet
  de la table.
- **Prévention :** Exiger que chaque migration sur une grande table en production indique explicitement quel
  lock elle prend et pour combien de temps, dans le cadre de la revue — et tester les migrations sur un
  jeu de données à l'échelle de la production en staging, pas seulement sur une base de dev vide ou petite, puisque la durée des locks
  croît avec la taille de la table.

### S6. Un utilisateur soumet un formulaire, est redirigé vers une page de confirmation, et constate que sa soumission est absente
- **Symptômes :** Intermittent, et spécifiquement lié aux flux écriture-puis-lecture-immédiate — le même
  utilisateur qui recharge un instant plus tard voit correctement les données.
- **Diagnostic :** Incohérence read-after-write classique d'une configuration naïve avec read replica (Q24) —
  l'écriture a atterri sur le primary, et la lecture de la page de confirmation a été routée vers un replica qui
  n'avait pas encore rattrapé.
- **Exemple :**
  ```java
  Long id = orderService.create(request);       // écriture -> primary
  return "redirect:/orders/" + id;               // le client suit immédiatement la redirection

  // Handler GET /orders/{id}, routé par le load balancer/read-router vers un replica :
  Order order = orderRepository.findById(id);    // le replica n'a pas encore répliqué l'insert -> 404
  ```
- **Résolution :** Router les lectures qui doivent refléter une écriture qui vient de se terminer vers le primary (ou un
  replica connu pour être à jour pour cette session), au moins pour ce flux précis.
- **Prévention :** Identifier explicitement, dès la conception, chaque flux sensible au read-after-write (ne pas
  supposer que toute lecture peut aller sans risque vers un replica), et surveiller le retard de réplication avec des alertes afin qu'un
  replica en retard soit détecté avant de causer une incohérence visible par les utilisateurs à grande échelle.

### S7. Deux requêtes quasi simultanées créent toutes deux une ligne pour ce qui devrait être une entité unique, produisant des doublons
- **Symptômes :** Sous charge concurrente (par ex. un utilisateur qui double-clique sur soumettre, ou une requête rejouée
  en course avec l'originale), deux lignes existent pour ce que la logique métier supposait ne pouvoir être
  qu'une seule (deux comptes pour un email, deux commandes pour une clé d'idempotence).
- **Diagnostic :** La logique check-then-insert au niveau applicatif (« vérifier si ça existe, sinon,
  insérer ») a une fenêtre de course entre la vérification et l'insertion — deux requêtes concurrentes peuvent toutes deux
  passer la vérification avant que l'une ait inséré.
- **Exemple :**
  ```java
  // Les deux requêtes exécutent ceci en concurrence et passent toutes deux la vérification avant que l'une insère :
  if (userRepository.findByEmail(email).isEmpty()) {
      userRepository.save(new User(email)); // fenêtre de course entre la vérification et cet insert
  }
  ```
- **Résolution :** Ajouter une contrainte d'unicité au niveau base (le pattern check-then-insert n'est jamais
  suffisant seul au niveau de concurrence réel de la base — la contrainte est la vraie garantie) et gérer l'exception
  de violation d'unicité résultante comme un cas attendu « existe déjà »,
  en utilisant `ON CONFLICT DO NOTHING`/`DO UPDATE` (upsert Postgres) quand l'intention est une création
  idempotente plutôt qu'une erreur franche.
  ```sql
  insert into users (email) values ('ann@example.com')
  on conflict (email) do nothing; -- idempotent face à la course exacte qui cassait check-then-insert
  ```
- **Prévention :** Ne jamais s'appuyer sur un check-then-act au niveau applicatif pour une unicité qui doit
  réellement tenir — toujours la doubler d'une contrainte en base, puisque la base est le seul
  composant capable de voir et de sérialiser des tentatives réellement concurrentes.

### S8. `SELECT COUNT(*)` sur une grande table est étonnamment lent et apparaît comme une requête chaude
- **Symptômes :** Un dashboard ou une fonctionnalité de pagination appelant `COUNT(*)` sur une table de plusieurs millions de lignes
  prend des secondes, ce qui est disproportionné par rapport à la simplicité apparente de la requête.
- **Diagnostic :** La conception MVCC de Postgres fait que `COUNT(*)` ne peut pas utiliser un index seul pour répondre
  à la question — il doit généralement vérifier la visibilité des lignes pour la transaction demandeuse, ce qui pour de
  grandes tables signifie un vrai scan d'une grande partie de la table (ou de l'index, pour un cas éligible à
  l'index-only-scan, mais toujours proportionnel au nombre de lignes dans les deux cas).
- **Exemple :**
  ```sql
  explain analyze select count(*) from orders;
  -- Aggregate (actual time=1120.44..1120.44 rows=1 loops=1)
  --   ->  Seq Scan on orders (actual time=0.01..980.22 rows=18000000 loops=1)

  -- Comptage approximatif depuis les statistiques de table — quasi instantané, suffisant pour la plupart des UI :
  select reltuples::bigint from pg_class where relname = 'orders';
  ```
- **Résolution :** Si des comptages exacts en temps réel ne sont pas réellement requis (la plupart des UI de pagination n'ont pas
  besoin d'un « 10 482 393 résultats » exact), utiliser un comptage approximatif issu des statistiques de table
  (`pg_class.reltuples`, rafraîchi par `ANALYZE`/autovacuum) ou plafonner et étiqueter les grands comptages (« 10 000+
  résultats ») au lieu de calculer le nombre exact. Si un comptage exact est réellement requis
  fréquemment, le maintenir de façon incrémentale (une colonne compteur mise à jour transactionnellement, ou via un
  agrégat matérialisé) plutôt que de le recalculer de zéro à chaque requête.
- **Prévention :** Traiter « a-t-on besoin d'un comptage exact à chaque chargement de page » comme une question de conception pour
  toute UI paginée sur une table grande ou à croissance rapide, pas comme un défaut à adopter sans réfléchir.

### S9. Les échecs de locking optimiste explosent pendant une période de fort trafic précise
- **Symptômes :** Les taux d'`OptimisticLockException` (ou d'erreur de conflit de version équivalente) grimpent
  pendant une fenêtre de forte concurrence connue (une vente flash, un événement populaire), causant une vague de
  mises à jour échouées que l'application remonte comme erreurs visibles par l'utilisateur ou comme retries silencieux.
- **Diagnostic :** Cela confirme en pratique le point de la Q16 — le taux d'échec du locking optimiste augmente
  avec la contention sur les mêmes lignes, et à une contention de niveau vente flash sur un petit nombre de lignes chaudes
  (par ex. des stocks limités), le taux d'échec peut devenir le problème d'expérience utilisateur dominant
  plutôt qu'un cas limite.
- **Exemple :**
  ```java
  // Course lecture-puis-écriture sous forte contention — chaque retry relit, revérifie, rééchoue :
  Inventory inv = inventoryRepository.findById(skuId); // lit la version N
  if (inv.getQty() > 0) { inv.setQty(inv.getQty() - 1); inventoryRepository.save(inv); }
  // save() lève OptimisticLockException si une autre requête a mis à jour cette ligne entre-temps

  // Correction pour ce chemin chaud précis : une seule instruction atomique, aucune course lecture-puis-écriture.
  ```
  ```sql
  update inventory set qty = qty - 1 where sku_id = ? and qty >= 1;
  -- 0 ligne affectée signifie « rupture de stock », sans lock détenu et sans tempête de retries possible
  ```
- **Résolution :** Pour les lignes réellement chaudes à forte contention spécifiquement, basculer ce chemin d'accès
  vers le locking pessimiste (ou une instruction atomique unique `UPDATE ... SET qty = qty - 1 WHERE qty >= 1`,
  qui contourne totalement la course lecture-puis-écriture du locking optimiste pour ce cas simple),
  tout en laissant le locking optimiste en place pour l'immense majorité des lignes à faible contention
  où il performe mieux.
- **Prévention :** Identifier les patterns de contention de lignes chaudes avant de les découvrir en production
  sous une vraie charge de vente flash — load-tester délibérément le chemin à forte contention, puisqu'il
  se comporte qualitativement différemment du trafic moyen.

### S10. Après un crash applicatif en pleine opération, la base est laissée dans un état incohérent
- **Symptômes :** Une opération métier en plusieurs étapes (débiter le compte A, créditer le compte B) est trouvée
  partiellement appliquée après un crash — un côté a eu lieu, l'autre non.
- **Diagnostic :** Les multiples instructions de l'opération n'étaient pas enveloppées dans une seule transaction en base
  — chacune s'est exécutée et a été commitée indépendamment, donc un crash entre elles a laissé un résultat
  réellement incohérent et non atomique ; c'est un bug de code applicatif, pas une défaillance de la base,
  puisque la base a fait exactement ce qu'on lui a demandé pour chaque instruction individuelle.
- **Exemple :**
  ```java
  // Bug : deux instructions auto-commit indépendantes, aucune frontière de transaction partagée.
  jdbcTemplate.update("update accounts set balance = balance - 100 where id = 1");
  // <-- un crash ici laisse le compte 1 débité et le compte 2 jamais crédité
  jdbcTemplate.update("update accounts set balance = balance + 100 where id = 2");

  // Correction : une transaction, atomique par construction.
  @Transactional
  void transfer(long fromId, long toId, BigDecimal amount) {
      jdbcTemplate.update("update accounts set balance = balance - ? where id = ?", amount, fromId);
      jdbcTemplate.update("update accounts set balance = balance + ? where id = ?", amount, toId);
  }
  ```
- **Résolution :** Envelopper toute l'opération en plusieurs étapes dans une seule transaction (`@Transactional` à
  la bonne granularité, ou un `BEGIN`/`COMMIT` explicite) pour que l'atomicité (Q5) tienne réellement —
  soit les deux instructions sont commitées, soit, en cas d'échec quelconque y compris un crash avant le commit, aucune ne l'est.
  Réconcilier manuellement les lignes incohérentes précises trouvées lors de cet incident, puisque les dégâts
  historiques ne sont pas corrigés automatiquement par le changement de code.
- **Prévention :** Traiter « cette opération est-elle enveloppée dans une seule transaction » comme une question de revue obligatoire
  pour tout code touchant plus d'une écriture, et ajouter un job de réconciliation/audit qui
  vérifie périodiquement exactement cette classe de dérive (par ex. des débits ne correspondant pas aux crédits) comme
  filet de sécurité indépendant du fait de bien faire chaque chemin de code du premier coup.

### S11. Les requêtes filtrant sur une colonne `JSONB` ralentissent à mesure que la table grossit, alors que la colonne est indexée
- **Symptômes :** Une requête comme `WHERE metadata @> '{"status": "active"}'` sur une colonne `JSONB`
  se dégrade avec la croissance de la table alors même qu'« il y a un index ».
- **Diagnostic :** Vérifier le type réel de l'index — un simple index B-tree sur une colonne `JSONB` ne supporte
  que l'égalité sur la valeur JSON *entière*, pas l'inclusion (`@>`) ni les requêtes d'existence de clé ; seul
  un index GIN (Q12) accélère réellement ces opérateurs. L'existence d'un index B-tree sur la colonne
  ne signifie pas que le pattern de requête précis l'utilise — `EXPLAIN` le confirme directement.
- **Exemple :**
  ```sql
  create index idx_orders_metadata on orders(metadata); -- B-tree — inutile pour @>

  explain select * from orders where metadata @> '{"status": "active"}';
  -- Seq Scan on orders -- l'index B-tree ci-dessus n'est même pas envisagé pour cet opérateur

  create index idx_orders_metadata_gin on orders using gin (metadata); -- la vraie correction
  ```
- **Résolution :** Ajouter spécifiquement un index GIN (`CREATE INDEX ... USING GIN (metadata)`, ou la
  variante `jsonb_path_ops` pour les requêtes d'inclusion uniquement, plus petite et plus rapide pour ce cas d'usage
  plus étroit).
- **Prévention :** Quand le pattern de requête d'une colonne implique des recherches d'inclusion/de clé plutôt que
  l'égalité sur la valeur entière, choisir délibérément dès le départ le type d'index pour cet opérateur,
  plutôt que d'ajouter « un index » de façon générique en supposant qu'il couvre tous les patterns d'accès.

### S12. Un job batch nocturne qui met à jour des millions de lignes une par une commence à expirer ou à submerger la base
- **Symptômes :** Un job batch qui boucle sur les lignes et émet un `UPDATE` par ligne prend
  de plus en plus de temps à mesure que le volume de données croît, et pendant son exécution les autres requêtes sur la même
  table ralentissent sensiblement.
- **Diagnostic :** Les updates ligne par ligne dans une boucle (le pattern de la Q20, mais pour des updates plutôt que
  des inserts) paient un surcoût d'aller-retour par instruction multiplié par le nombre de lignes, et si chaque update
  est commité individuellement, cela génère aussi bien plus de churn write-ahead-log/vacuum que nécessaire ;
  si tout est dans une seule transaction géante, cela crée une transaction de longue durée qui détient des
  locks et fait gonfler la table (puisque Postgres ne peut pas vacuumer des lignes qu'une transaction de longue durée pourrait
  encore avoir besoin de voir).
- **Exemple :**
  ```java
  // Un aller-retour par ligne, et — si enveloppé dans une seule transaction géante — une transaction
  // de longue durée qui bloque autovacuum pendant toute sa durée.
  for (Long id : millionsOfIds) {
      jdbcTemplate.update("update prices set updated = true where id = ?", id);
  }
  ```
  ```sql
  -- Correction : une seule instruction en masse au lieu d'un million d'aller-retours.
  update prices set updated = true
  from (values (1), (2), (3) /* ... les ids d'un lot ... */) as t(id)
  where prices.id = t.id;
  ```
- **Résolution :** Batcher les updates — soit une seule instruction `UPDATE ... FROM (VALUES ...)` en masse
  pour tout l'ensemble, soit des lots par tranches de quelques milliers de lignes, commités
  de façon incrémentale plutôt qu'en une seule transaction tout-ou-rien, avec une courte pause entre les lots si
  l'objectif est d'éviter de saturer la base pendant les heures ouvrées.
- **Prévention :** Adopter par défaut pour tout job de modification de données en masse un pattern par tranches et par lots dès le
  départ, avec taille de tranche et rythme configurables — « boucler et mettre à jour une ligne à la fois » devrait
  être un drapeau de revue de code pour tout ce qui opère sur plus de quelques centaines de lignes.

### S13. Un rapport affiche parfois des chiffres qui ne concordent pas, uniquement sous activité d'écriture concurrente
- **Symptômes :** Un rapport multi-requêtes (par ex. la somme de valeurs de plusieurs tables qui devraient se réconcilier) est
  correct quand le système est inactif mais parfois incohérent quand il est généré pendant que des écritures ont lieu
  en concurrence.
- **Diagnostic :** Vérifier le niveau d'isolation sous lequel s'exécutent les requêtes du rapport — au niveau par défaut Read
  Committed (Q15), chaque instruction individuelle de la transaction du rapport voit les dernières données
  commitées *au moment où cette instruction précise s'exécute*, donc deux requêtes espacées de quelques
  millisecondes au sein du même « rapport » peuvent voir des snapshots différents si une écriture est commitée
  entre-temps — c'est un non-repeatable read, pas un bug dans l'arithmétique du rapport.
- **Exemple :**
  ```sql
  -- Rapport, exécuté au niveau Read Committed par défaut :
  select sum(amount) from debits;   -- voit 10 000 $ au total

  -- Une écriture est commitée ici, entre les deux instructions du rapport :
  -- insert into credits (amount) values (500);

  select sum(amount) from credits;  -- inclut maintenant les nouveaux 500 $ -- les deux sommes ne concordent plus
  ```
- **Résolution :** Exécuter tout le rapport dans une seule transaction en isolation Repeatable Read
  (le Repeatable Read de Postgres prend un snapshot cohérent unique pour toute la transaction), de sorte que chaque
  requête à l'intérieur voit exactement la même vue à un instant donné des données.
  ```sql
  begin transaction isolation level repeatable read;
  select sum(amount) from debits;
  select sum(amount) from credits; -- garanti de voir le même snapshot que la première requête
  commit;
  ```
- **Prévention :** Toute opération multi-requêtes nécessitant une vue cohérente unique des données
  sur plusieurs instructions demande une décision explicite de niveau d'isolation, pas le défaut implicite
  — c'est un cas où nommer le niveau d'isolation en revue de code compte autant que nommer la
  stratégie d'index.

### S14. Les tailles des tables et index ne cessent de croître alors que le nombre de lignes est à peu près stable
- **Symptômes :** L'utilisation disque d'une table fréquemment mise à jour grimpe régulièrement, de façon disproportionnée par rapport à
  son nombre réel de lignes vivantes (stable ou à croissance lente), et les performances des requêtes se dégradent en parallèle.
- **Diagnostic :** C'est du bloat de table/index — le MVCC de Postgres conserve les anciennes versions de lignes (dead tuples)
  après un `UPDATE`/`DELETE` jusqu'à ce que vacuum les récupère ; si autovacuum ne suit pas
  (trop peu fréquent pour le rythme d'écriture de la table, ou bloqué par une transaction de longue durée qui retient
  l'horizon jusqu'auquel il peut nettoyer), les dead tuples s'accumulent et font à la fois gonfler la table sur disque
  et dégradent chaque scan qui doit les sauter.
- **Exemple :**
  ```sql
  select relname, n_live_tup, n_dead_tup
  from pg_stat_user_tables
  where relname = 'sessions';
  --  relname  | n_live_tup | n_dead_tup
  --  sessions |    500000  |   4200000   -- 8x plus de dead tuples que de lignes vivantes
  ```
- **Résolution :** Régler autovacuum de façon plus agressive pour cette table précise
  (overrides par table de `autovacuum_vacuum_scale_factor`/`cost_limit` pour les tables à fort churn plutôt que
  le défaut global), identifier et corriger toute transaction de longue durée empêchant vacuum de
  progresser, et lancer un `VACUUM (VERBOSE, ANALYZE)` manuel pour évaluer le bloat actuel et
  récupérer de l'espace disque (ou `VACUUM FULL`/`pg_repack` pour les cas sévères, en sachant que `VACUUM FULL`
  prend un lock exclusif).
- **Prévention :** Surveiller le nombre de dead tuples et la fréquence d'exécution d'autovacuum par table comme métrique continue
  pour toute table à forte écriture, pas seulement la taille globale de la table — le bloat est une tendance peu coûteuse à
  détecter tôt et coûteuse à résorber une fois sévère.

### S15. Supprimer une ligne supprime de façon inattendue un grand nombre de lignes liées dans plusieurs tables
- **Symptômes :** Supprimer ce qui ressemblait à une entité unique et isolée (par ex. supprimer un utilisateur)
  se propage en cascade en supprimant des commandes, des enregistrements de paiement ou un historique d'audit que l'équipe pensait
  préservés.
- **Diagnostic :** Vérifier le comportement `ON DELETE` des contraintes de clés étrangères — `ON DELETE CASCADE`
  a été défini (peut-être pour une autre relation réellement dépendante, comme des lignes de commande appartenant
  à une commande) et il se propage désormais plus loin que prévu à travers une chaîne de clés
  étrangères en cascade, ou a été appliqué à une relation qui aurait dû être `ON DELETE RESTRICT`
  (bloquer la suppression) ou `SET NULL`.
- **Exemple :**
  ```sql
  -- users -> orders -> payments, CASCADE à chaque maillon :
  alter table orders add constraint fk_orders_user
      foreign key (user_id) references users(id) on delete cascade;
  alter table payments add constraint fk_payments_order
      foreign key (order_id) references orders(id) on delete cascade;

  delete from users where id = 42; -- supprime aussi silencieusement chaque commande ET chaque enregistrement de paiement
  ```
- **Résolution :** Passer en revue chaque `ON DELETE CASCADE` de la chaîne concernée et le changer en
  `RESTRICT` (forcer une décision explicite au moment de la suppression) ou `SET NULL` partout où la cascade n'est pas
  réellement le comportement métier voulu ; pour les entités nécessitant une rétention historique, c'est
  généralement aussi le déclencheur pour introduire des soft deletes (Q27) plutôt que de les hard-delete
  du tout.
- **Prévention :** Traiter `ON DELETE CASCADE` comme une décision délibérée et revue pour chaque relation,
  pas comme un défaut adopté par commodité — documenter explicitement, pour chaque clé étrangère, ce qui doit
  arriver aux lignes filles quand le parent est supprimé.

### S16. Immédiatement après un déploiement incluant une migration de schéma, l'application se met à lever des erreurs sur une colonne manquante ou inattendue
- **Symptômes :** Des erreurs comme « column does not exist » ou un échec de mapping apparaissent juste après
  le déploiement, mais seulement sur certaines instances, ou seulement brièvement.
- **Diagnostic :** Le déploiement de la migration et celui du code applicatif ne sont pas atomiques ensemble — pendant un
  déploiement rolling, d'anciennes instances applicatives (attendant l'ancien schéma) peuvent encore tourner
  sur une base déjà migrée vers le nouveau schéma, ou une migration a été exécutée
  *après* que le nouveau code applicatif s'attendait déjà à elle, exposant brièvement un trou.
- **Exemple :**
  ```
  ERROR: column "region" of relation "orders" does not exist
  ```
  Une nouvelle instance applicative, déjà déployée et attendant `orders.region`, a commencé à recevoir
  du trafic avant que la migration ajoutant cette colonne ait réellement été exécutée sur la base — ou
  l'inverse : d'anciennes instances exécutant encore la version précédente s'étranglent sur une colonne renommée/supprimée
  par une migration déjà appliquée.
- **Résolution :** Réordonner strictement le déploiement pour que la migration se termine toujours complètement avant que
  tout nouveau code applicatif qui en dépend ne reçoive du trafic, et s'assurer que la migration
  elle-même est rétrocompatible avec l'*ancienne* version de l'application pendant toute la durée où d'anciennes instances
  tournent encore (c'est exactement pourquoi le pattern de migration en plusieurs étapes, additif d'abord, de la Q32
  compte — il est conçu pour que l'ancien comme le nouveau code fonctionnent avec l'état de schéma intermédiaire).
- **Prévention :** Ne jamais livrer une migration qui à la fois ajoute une exigence (une nouvelle colonne `NOT NULL`, une
  colonne renommée) et requiert le nouveau code dans la même étape atomique — toujours scinder en une migration
  additive et rétrocompatible d'abord, déployée et vérifiée, avant qu'une migration de nettoyage ultérieure ne supprime ce dont
  l'ancien code avait besoin.

### S17. Un rapport « clients qui n'ont jamais commandé » retourne soudainement zéro ligne
- **Symptômes :** Une requête marketing qui listait ~12 000 clients sans commande chaque semaine
  retourne maintenant un résultat vide. Personne n'a modifié la requête et il n'y a eu aucune erreur ; les nombres de clients
  et de commandes semblent normaux.
- **Diagnostic :** Un résultat vide d'une requête qui *devrait* retourner des lignes, juste après un changement
  de données, pointe vers `NOT IN` et `NULL` (Q10). Regarder ce qui a changé dans les données : une nouvelle fonctionnalité de « guest
  checkout » a commencé à insérer des commandes avec `customer_id IS NULL`. Confirmer avec
  `select count(*) from orders where customer_id is null;` — et vérifier le plan, qui montre un
  filtre `NOT (hashed SubPlan)`. Un seul `NULL` dans la sous-requête rend `id <> NULL` inconnu pour chaque
  client, donc `NOT IN` les rejette tous.
- **Exemple :**
  ```sql
  select id, email
  from customers
  where id not in (select customer_id from orders);   -- 0 ligne dès qu'un customer_id vaut NULL
  ```
- **Résolution :** Réécrire en anti-jointure sûre vis-à-vis de `NULL` et relancer le rapport pour confirmer que les
  ~12 000 lignes reviennent :
  ```sql
  select c.id, c.email
  from customers c
  where not exists (select 1 from orders o where o.customer_id = c.id);
  -- ou :  left join orders o on o.customer_id = c.id  where o.id is null
  ```
  Décider aussi si `orders.customer_id` *devrait* être nullable ; si les commandes invité sont légitimes,
  les modéliser explicitement plutôt qu'avec une clé étrangère `NULL`.
- **Prévention :** Règle d'équipe : pas de `NOT IN (subquery)` — utiliser `NOT EXISTS`. Ajouter un contrôle lint/revue pour
  cela ; ajouter une fixture de test incluant des `NULL` dans chaque colonne nullable utilisée dans une sous-requête ; et
  imposer `NOT NULL` sur les colonnes qui ne sont jamais censées être vides.

### S18. Un feed à scroll infini et un export CSV ralentissent chaque semaine, et les utilisateurs voient des lignes répétées ou manquantes
- **Symptômes :** L'écran d'admin « audit events » et un export nocturne utilisent tous deux la pagination. Charger
  les dernières pages prend maintenant 8+ secondes et la base montre des pics CPU périodiques chaque fois qu'un
  crawler ou un export parcourt la liste. Par ailleurs, le fichier d'export contient certaines lignes en double et en
  manque d'autres.
- **Diagnostic :** `EXPLAIN (ANALYZE, BUFFERS)` de la requête de page lente montre un index scan (ou un
  tri) qui retourne ~1 000 050 lignes et un nœud `Limit` jetant tout sauf 50 — le coût est
  proportionnel à l'offset (Q11). Les doublons/lignes manquantes sont la moitié « instabilité » : de nouveaux événements
  ont été insérés en haut pendant que l'export paginait, décalant chaque page suivante du nombre de
  nouvelles lignes. Les deux symptômes viennent de la même conception par `offset`.
- **Exemple :**
  ```sql
  explain (analyze, buffers)
  select id, created_at, action from audit_events
  order by created_at desc, id desc
  offset 1000000 limit 50;
  -- Limit  (actual rows=50)
  --   -> Index Scan ... (actual rows=1000050)   <- le travail croît avec l'offset
  ```
- **Résolution :** Passer à la pagination keyset avec un index composite correspondant au tri, et
  retourner un curseur opaque (le dernier `(created_at, id)`) au client :
  ```sql
  create index concurrently audit_events_seek_idx on audit_events (created_at desc, id desc);

  select id, created_at, action from audit_events
  where (created_at, id) < (:c_at, :c_id)
  order by created_at desc, id desc
  limit 50;
  ```
  Pour l'export, paginer par keyset (ou utiliser un curseur côté serveur / `COPY`) pour qu'un insert concurrent
  ne puisse pas décaler les pages. Vérifier avec `EXPLAIN` que la latence est plate entre la page 1 et la page 20 000 et
  relancer l'export sous une charge d'insertion réelle, en comparant les nombres de lignes et en vérifiant l'absence de doublons.
- **Prévention :** Plafonner `page`/`size` dans l'API, préférer la pagination par curseur pour toute
  liste non bornée, et intégrer au pipeline un test de charge de la page la *plus profonde*. Pour les UI qui doivent
  offrir des numéros de page, limiter la profondeur atteignable (par ex. les 100 premières pages) et orienter les utilisateurs vers des filtres de recherche.

### S19. `ALTER TABLE` reste bloqué, les déploiements calent et l'app ralentit, avec des dizaines de sessions « idle in transaction »
- **Symptômes :** Une migration de routine attend indéfiniment et toute la table `orders` devient
  non réactive derrière elle. `pg_stat_activity` montre des connexions à l'état `idle in transaction`,
  certaines depuis des heures. L'utilisation du pool de connexions est élevée alors que le CPU et les I/O sont faibles, et le bloat de la table
  continue de croître (S14).
- **Diagnostic :** Une session qui a commencé une transaction puis est restée silencieuse conserve les locks qu'elle a pris
  (et retient l'horizon de vacuum). La migration a besoin d'un lock `ACCESS EXCLUSIVE`, se met en file derrière
  une telle session, puis chaque *nouvelle* requête se met en file derrière la migration — d'où le blocage total.
  Trouver les coupables et qui bloque qui :
  ```sql
  select pid, state, now() - xact_start as tx_age, left(query, 80) as last_query
  from pg_stat_activity
  where state = 'idle in transaction'
  order by xact_start;

  select pid, pg_blocking_pids(pid) as blocked_by, wait_event_type, left(query, 60)
  from pg_stat_activity where cardinality(pg_blocking_pids(pid)) > 0;
  ```
  Faire correspondre le `last_query` le plus ancien au code : typiquement une méthode `@Transactional` qui fait un appel
  HTTP lent ou attend une saisie utilisateur après sa première requête, ou une connexion fuitée sans
  `commit`/`rollback` (module 2 Q17 pour la variante OSIV).
- **Exemple :**
  ```java
  @Transactional                                     // la transaction s'ouvre à la première requête
  public void checkout(long orderId) {
      Order o = orders.findById(orderId).orElseThrow();   // prend un lock de ligne plus tard au moment de l'update
      paymentGateway.charge(o);                            // appel HTTP de 20 s À L'INTÉRIEUR de la transaction
      o.markPaid();
  }
  ```
- **Résolution :** Immédiat : terminer les plus anciens fautifs (`select pg_terminate_backend(pid)`),
  ce qui permet à la migration en file de se poursuivre. Correction de fond : garder des transactions courtes — faire l'appel distant
  *en dehors* de la transaction (ou utiliser un outbox), et exécuter les migrations avec un `lock_timeout` pour qu'elles
  échouent vite au lieu de bloquer tout le monde (Q25). Vérifier que le nombre de sessions `idle in transaction`
  revient à ~0 sous charge.
- **Prévention :** Définir `idle_in_transaction_session_timeout` (par ex. 30 s) au niveau du rôle comme filet
  de sécurité, `lock_timeout` dans l'outillage de migration, alerter sur l'âge des transactions et sur le nombre de
  `idle in transaction`, et interdire les appels réseau dans les méthodes `@Transactional` en revue.

### S20. Deux workers traitent le même job en file, et parfois un worker reste bloqué à attendre l'autre
- **Symptômes :** Une flotte de workers basée sur une table `jobs` envoie parfois la même facture deux fois.
  Après l'ajout de workers, le débit s'améliore à peine et certains workers montrent de longues attentes, tandis que
  d'autres ne traitent rien.
- **Diagnostic :** Lire la requête de claim. Un simple `select ... where status = 'PENDING' limit 10`
  suivi d'un `update` est une course check-then-act : deux workers lisent les mêmes lignes avant que l'un
  les mette à jour. Ajouter `for update` sans `skip locked` corrige la double lecture mais fait
  *attendre* le second worker sur les locks de lignes du premier — sérialisant toute la flotte (Q17). Confirmer dans
  `pg_stat_activity` (`wait_event_type = 'Lock'`, en attente sur `transactionid`).
- **Exemple :**
  ```sql
  -- Course : les deux workers obtiennent les mêmes 10 ids.
  select id from jobs where status = 'PENDING' order by id limit 10;
  update jobs set status = 'RUNNING' where id = any(:ids);
  ```
- **Résolution :** Réclamer atomiquement avec `FOR UPDATE SKIP LOCKED` dans une seule instruction (voir
  Q17), commiter le claim, traiter en dehors de la transaction, et ajouter un reaper pour les leases expirés.
  Puisque la livraison est désormais at-least-once, rendre le handler idempotent en enregistrant l'id de la facture avec
  une contrainte d'unicité avant l'envoi. Vérifier avec un test qui lance 8 workers sur 10 000
  jobs et asserte que chaque id de job a été traité exactement une fois et que le temps total diminue avec
  davantage de workers.
- **Prévention :** Placer la requête de claim derrière une seule méthode de repository testée ; load-tester avec
  des workers concurrents avant d'ajouter le second ; à plus fort volume, passer à un vrai broker
  (module 4) plutôt que d'étendre les responsabilités de la table-queue.

### S21. Les inserts se mettent à échouer avec `duplicate key value violates unique constraint "orders_pkey"` après un import de données
- **Symptômes :** Après avoir restauré un sous-ensemble de la production en staging (ou chargé un CSV legacy),
  l'app échoue sur les premières nouvelles commandes : `ERROR: duplicate key value violates unique
  constraint "orders_pkey" — Key (id)=(10001) already exists`. Elle échoue par intermittence, puis
  réussit une fois que les ids « rattrapent » — mais seulement après plusieurs requêtes échouées.
- **Diagnostic :** La séquence derrière le défaut de `id` est indépendante du contenu de la table.
  Importer des lignes avec des ids *explicites* (ou une restauration data-only) les insère sans faire avancer la
  séquence, donc `nextval()` distribue des valeurs qui existent déjà. Comparer
  `select last_value from orders_id_seq;` avec `select max(id) from orders;` — une séquence derrière max
  le confirme. (À part : les trous dans les ids sont normaux et *pas* un bug — les inserts annulés (rollback) consomment quand même
  des valeurs de séquence.)
- **Exemple :**
  ```sql
  insert into orders (id, customer_id, total) values (10001, 7, 99.90);   -- id explicite
  insert into orders (customer_id, total) values (8, 15.00);
  -- -> nextval() retourne 1, 2, 3 ... jusqu'à entrer en collision avec 10001
  ```
- **Résolution :** Réaligner la séquence sur les données :
  ```sql
  select setval(pg_get_serial_sequence('orders', 'id'), (select coalesce(max(id), 1) from orders));
  ```
  Vérifier en insérant une nouvelle ligne et en contrôlant qu'elle reçoit un id supérieur au maximum importé ; exécuter la
  même vérification pour chaque table qui a été importée.
- **Prévention :** Terminer chaque script d'import/migration qui fournit des ids par une étape `setval`
  (ou ne pas fournir d'ids) ; inclure une requête de sanity post-import qui compare chaque séquence à
  `max(id)` ; ne pas compter sur des ids sans trou pour un sens métier (les numéros de facture ont besoin de leur propre
  schéma de numérotation sans trou).

### S22. Un rapport qui prenait 2 secondes toute la semaine prend 20 minutes le lundi matin, sans aucun changement de code
- **Symptômes :** Après le chargement en masse du week-end (~20 millions de lignes importées dans `transactions`),
  la même requête de dashboard est soudainement 500x plus lente et sature le CPU. Un `EXPLAIN` d'un collègue quelques
  heures plus tard montre un plan rapide.
- **Diagnostic :** Comparer les lignes estimées vs réelles dans `EXPLAIN (ANALYZE)` (Q14). Ici le planner
  a estimé `rows=1` pour un filtre qui retournait réellement 2 000 000 et a choisi un nested loop qui a fait
  2 millions de recherches d'index, là où un hash join aurait été le bon choix. Cause : le chargement en masse
  a changé la distribution des données mais l'auto-analyze d'autovacuum n'avait pas encore rafraîchi les statistiques
  de la table (il se déclenche après ~10 % de lignes modifiées *et* se termine selon son propre calendrier). Le
  plan rapide est apparu plus tard parce que l'auto-analyze a fini par s'exécuter. Vérifier
  `select last_autoanalyze, n_mod_since_analyze from pg_stat_user_tables where relname = 'transactions';`.
- **Exemple :**
  ```sql
  explain (analyze)
  select * from transactions t join accounts a on a.id = t.account_id
  where t.batch_id = 991;
  -- Nested Loop (rows=1) (actual rows=2000000) -> le planner se trompe de 6 ordres de grandeur
  ```
- **Résolution :** Exécuter `ANALYZE transactions;` immédiatement — le plan bascule vers un hash join en
  quelques secondes — et revérifier le temps de la requête. Si les erreurs d'estimation persistent pour des colonnes corrélées (par ex.
  `country` et `currency`), créer des statistiques étendues
  (`create statistics tx_corr (dependencies) on country, currency from transactions;`) et/ou
  augmenter `default_statistics_target` pour les colonnes asymétriques.
- **Prévention :** Faire de `ANALYZE` la dernière étape de chaque job de chargement en masse ; abaisser
  `autovacuum_analyze_scale_factor` pour les très grandes tables ; ajouter une alerte sur les grands écarts entre
  lignes estimées et réelles dans les slow-query logs (`auto_explain` avec `log_analyze`), et comparer
  les plans en staging avec des données à l'échelle de la production.

## 📌 Cheat-sheet

- **JPA vs JDBC vs MyBatis** : ORM complet / bas niveau manuel / SQL-que-vous-écrivez-plus-mapping — choisir selon le niveau de contrôle dont vous avez besoin sur le SQL exact.
- **Ordre logique SQL** : `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`. `WHERE` ne voit pas un alias de `SELECT` ; `HAVING` peut filtrer les agrégats car il s'exécute après le regroupement.
- **N+1** : 1 requête devient N+1 via des collections chargées en lazy dans une boucle — corriger avec `JOIN FETCH`/`@EntityGraph`/batch fetching, pas avec un `FetchType.EAGER` généralisé.
- **Optimiste vs pessimiste** : l'optimiste gagne à faible contention (aucun lock détenu) ; le pessimiste gagne à forte contention sur les mêmes lignes chaudes (évite les tempêtes de retries).
- **États d'entité Hibernate** : transient → persistent (managed, suivi automatique) → detached (changements non suivis — `merge()` peut écraser silencieusement des données plus récentes) → removed.
- **`@Transactional` multi-datasource** ne couvre pas atomiquement les deux bases sans JTA/XA — concevoir plutôt autour d'une source de vérité unique par écriture.
- **Types d'index Postgres** : B-tree (défaut, égalité/plage) · GIN (inclusion JSONB, plein texte, tableaux) · GiST (géométrique/chevauchement de plages) · index partiel (petit, sous-ensemble filtré).
- **`EXPLAIN ANALYZE`** : surveiller un `Seq Scan` sur une grande table, et les écarts lignes estimées vs réelles (stats obsolètes → lancer `ANALYZE`) — un `EXPLAIN` simple n'est qu'une estimation, il n'exécute jamais la requête.
- **Niveaux d'isolation** : Read Committed (défaut, ne prévient que les dirty reads) < Repeatable Read (prévient aussi les non-repeatable/phantom reads dans Postgres) < Serializable (équivalent totalement série, plus de retries).
- **Dimensionnement HikariCP** : plus petit que ce que l'intuition suggère ; le total des connexions sur toute la flotte doit tenir dans le `max_connections` de la base, pas seulement dans le pool d'une instance.
- **Grosses migrations** : `NOT VALID` + `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`, additif-puis-backfill-puis-nettoyage — jamais une seule étape bloquante sur une énorme table en production.
- **L'ordre des colonnes d'un index composite** compte : colonnes d'égalité/haute sélectivité d'abord, sinon l'index ne sert silencieusement pas la requête.
- **JSONB** : correct pour des données éparses/variables ; normaliser tout ce qui est fréquemment filtré, joint ou vérifié par contrainte.
- **Écritures en masse** : batcher inserts/updates (API de batch JDBC, `VALUES` multi-lignes, ou `COPY`) — jamais ligne par ligne dans une boucle ; `hibernate.jdbc.batch_size` seul ne suffit pas sans `order_inserts`/`order_updates`.
- **Read replicas** : un routage naïf casse le read-after-write — épingler les lectures sensibles aux écritures sur le primary.
- **`ON DELETE CASCADE`** : une décision délibérée par relation, pas un défaut — passer en revue toute la chaîne de cascade.
- **Soft deletes** : empêchent que des filtres `deleted_at is null` oubliés et des contraintes d'unicité ne fuient/bloquent sur des lignes « supprimées » — limiter l'unicité aux lignes actives avec un index partiel.
- **Bloat de table/index** : `n_dead_tup` qui croît malgré un `n_live_tup` stable signifie qu'autovacuum ne suit pas — régler les paramètres par table ou trouver la transaction de longue durée bloquante.
- **Changements de schéma sans interruption** : additif/nullable d'abord → backfill → application/nettoyage, chaque étape compatible avec l'ancien et le nouveau code applicatif.
- **`LEFT JOIN` + `WHERE` sur la table de droite** le transforme en jointure interne — mettre la condition dans `ON` ; utiliser `WHERE right.id IS NULL` pour les anti-jointures.
- **`UNION ALL` par défaut** : `UNION` ajoute une passe de déduplication par tri/hash et peut fusionner des lignes légitimement répétées.
- **`NULL` signifie « inconnu »** : `= NULL` ne correspond jamais, `<>` écarte les lignes `NULL`, `NOT IN (subquery avec NULL)` ne retourne rien (utiliser `NOT EXISTS`), `count(col)` ≠ `count(*)`, `UNIQUE` autorise de nombreux `NULL` (PG15 `NULLS NOT DISTINCT`).
- **Pagination** : `OFFSET` coûte O(offset) et se décale sous les écritures — utiliser keyset (`where (created_at, id) < (...)`) avec un index composite correspondant et un départage unique.
- **`FOR UPDATE SKIP LOCKED`** = work queue Postgres : claim court, traitement hors transaction, ajout d'un reaper de leases — at-least-once, donc handlers idempotents.
- **Partitionnement** : rentable pour la rétention (drop partition) et le pruning ; la PK doit inclure la clé de partition, les requêtes doivent filtrer dessus, créer les partitions à l'avance — ne pas partitionner avant que ça fasse mal.
- **Clés primaires** : `bigint` = compact et local à l'insertion ; UUIDv4 = splits de pages aléatoires ; UUIDv7 = distribué *et* à peu près ordonné ; `IDENTITY` désactive le batching d'inserts Hibernate.
- **Boîte à outils d'index** : composite (égalité d'abord, plage en dernier), partiel (sous-ensemble chaud), couvrant `INCLUDE` (l'index-only scan nécessite une visibility map à jour), d'expression (`lower(email)`), GIN trigram pour `LIKE '%x%'` ; construire avec `CONCURRENTLY`, supprimer les inutilisés.
- **Les sessions `idle in transaction`** détiennent des locks et l'horizon de vacuum — elles font caler les migrations ; définir `idle_in_transaction_session_timeout` et `lock_timeout`, garder les appels distants hors des transactions.
- **Les ids explicites ne font pas avancer la séquence** — `setval` après les imports ; les trous dans les ids sont normaux.
- **Bascule de plan après un chargement en masse** = statistiques obsolètes : `ANALYZE` à la fin des jobs batch, statistiques étendues pour les colonnes corrélées, comparer lignes estimées vs réelles.
