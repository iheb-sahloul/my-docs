# Persistance & SQL

## 🟢 Fondamentaux

### Choix d'ORM & d'accès aux données

#### Q1. Qu'est-ce qu'un ORM, et quel problème résout-il réellement ? {#orm-problem-solve}
**Réponse :** Un ORM (Object-Relational Mapper) comble le « décalage d'impédance » entre le modèle relationnel
(tables, lignes, clés étrangères) et le modèle objet (classes, références, héritage) — en mappant
les lignes vers des objets, les clés étrangères vers des références/collections d'objets, et en traduisant la
navigation dans le graphe d'objets en jointures SQL ou en requêtes supplémentaires. Il résout le côté fastidieux et
sujet aux erreurs de l'écriture manuelle de ce code de mapping pour chaque entité, au prix de la génération
occasionnelle d'un SQL moins efficace qu'une requête écrite à la main pour un cas précis (voir le problème N+1, Q29).

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
sont précisément l'endroit où naît le problème N+1 (Q29).

#### Q2. Quand choisiriez-vous JPA/Hibernate, JDBC pur ou MyBatis ? {#jpa-hibernate-plain-jdbc-mybatis}
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

#### Q3. Quelle est la différence entre une clé primaire, une contrainte d'unicité et un index ? {#primary-key-unique-constraint-index}
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

#### Q4. Détaillez la normalisation d'une table de la 1NF à la 3NF. {#normalizing-table-1nf-3nf}
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
à peine, est exactement le cas où la dénormalisation délibérée (Q45) est le choix le plus senior.

#### Q5. Que garantissent réellement les propriétés ACID ? {#acid-properties-guarantee}
**Réponse :** **Atomicité** : les opérations d'une transaction réussissent toutes ou sont toutes annulées (rollback) ensemble, sans
application partielle. **Cohérence** : une transaction fait passer la base d'un état valide à un autre,
en respectant les contraintes (clés étrangères, contraintes d'unicité, contraintes check). **Isolation** :
les transactions concurrentes ne voient pas l'état intermédiaire non validé les unes des autres, dans une mesure
contrôlée par le niveau d'isolation (Q25). **Durabilité** : une fois validées (commit), les changements d'une transaction
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

#### Q6. Quelle est la différence entre `INNER JOIN` et `LEFT JOIN`, et pourquoi une clause `WHERE` peut-elle silencieusement transformer un `LEFT JOIN` en jointure interne ? {#inner-join-left-join-clause}
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

#### Q7. Quelle est la différence entre `UNION` et `UNION ALL`, et lequel devrait être votre choix par défaut ? {#union-union-all-default}
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

#### Q8. Quel est l'ordre d'exécution logique des clauses d'une requête SQL — et pourquoi ne peut-on pas filtrer sur un alias de `SELECT` dans `WHERE` ? {#logical-execution-order-sql-query}
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

#### Q9. Pourquoi peut-on filtrer sur une fonction d'agrégation dans `HAVING` mais pas dans `WHERE` ? {#filter-aggregate-function-having-but}
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

#### Q10. Quels sont les pièges classiques de `NULL` en SQL, et comment éviter chacun ? {#classic-null-traps-sql-avoid}
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

#### Q11. Pourquoi la pagination par `OFFSET` devient-elle plus lente — et moins correcte — à mesure qu'on va en profondeur, et quelle est l'alternative ? {#offset-pagination-get-slower-less}
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

### Patterns de requêtes SQL (les classiques demandés en direct)

Ce sont les requêtes qu'un intervieweur vous demande d'écrire au tableau ou dans un éditeur partagé. Tous les exemples
utilisent le même petit schéma, que vous pouvez coller dans n'importe quel PostgreSQL :

```sql
customers  (id, name, email, country, created_at)
orders     (id, customer_id, status, total, created_at)
order_items(order_id, product_id, quantity, unit_price)
products   (id, name, category_id, price)
departments(id, name)
employees  (id, name, salary, department_id, manager_id)
logins     (user_id, login_date)
```

Annoncez d'abord l'approche à voix haute (quelles lignes, groupées comment, triées comment), écrivez ensuite la requête, puis
nommez le cas limite (égalités, `NULL`, groupes vides). C'est cet ordre qui est évalué.

#### Q12. Expliquez les fonctions de fenêtrage : `row_number` vs `rank` vs `dense_rank`, totaux cumulés, `lag`, et le piège de la frame par défaut. {#window-functions-row-number-rank}
**Réponse :** Une fonction de fenêtrage calcule une valeur *par ligne* sur un ensemble de lignes liées (la fenêtre) **sans
réduire les lignes** comme le fait `GROUP BY`. `PARTITION BY` définit les groupes, `ORDER BY` l'ordre à l'intérieur de
chacun, et la frame optionnelle (`ROWS`/`RANGE BETWEEN …`) les lignes utilisées pour chaque calcul. Les fonctions de rang
ne diffèrent que sur les égalités : avec des salaires 100, 100, 90 → `row_number` = 1,2,3 (toujours unique, arbitraire
entre égalités), `rank` = 1,1,3 (les égalités partagent un rang, puis un trou), `dense_rank` = 1,1,2 (sans trou). `lag(x, n)` /
`lead(x, n)` lisent la ligne précédente/suivante ; `sum(x) over (order by …)` donne un total cumulé ;
`first_value` / `last_value` / `ntile(4)` couvrent « premier du groupe » et les quartiles. Comme les fenêtres s'exécutent
après `WHERE`/`GROUP BY`/`HAVING` (Q8), on ne peut pas filtrer dessus directement — il faut envelopper la requête dans une sous-requête
ou une CTE et filtrer à l'extérieur.

**Exemple :**

```sql
-- Rang dans chaque département ; la fenêtre nommée évite de répéter la clause.
select name, department_id, salary,
       row_number() over w as rn,
       rank()       over w as rnk,
       dense_rank() over w as drnk
from employees
window w as (partition by department_id order by salary desc);

-- CA quotidien, total cumulé et variation par rapport à la veille.
with daily as (
    select created_at::date as day, sum(total) as revenue
    from orders group by 1
)
select day, revenue,
       sum(revenue) over (order by day rows unbounded preceding) as running_revenue,
       revenue - lag(revenue) over (order by day)                as delta_vs_yesterday
from daily;
```

**Pourquoi c'est un piège :** avec `ORDER BY` et sans frame explicite, la valeur par défaut est `RANGE BETWEEN UNBOUNDED
PRECEDING AND CURRENT ROW`, qui inclut toutes les lignes *paires* (valeurs d'ordre égales) — un total cumulé sur une
colonne non unique saute donc de tout le groupe d'égalité, et `last_value()` renvoie la ligne courante et non la
dernière de la partition. Écrivez explicitement `rows unbounded preceding` (ou `rows between unbounded preceding and unbounded
following` pour `last_value`).

#### Q13. Écrivez « le Nième salaire le plus élevé » et « les 3 mieux payés par département ». Comment les égalités changent-elles la réponse ? {#write-nth-highest-salary-top}
**Réponse :** Commencez par clarifier la **sémantique des égalités** — « deuxième salaire *distinct* le plus élevé » et « deuxième ligne
dans l'ordre des salaires » sont deux questions différentes. Pour un Nième distinct, `dense_rank()` dans une sous-requête est la
réponse générale et lisible ; `distinct … order by … offset n-1 limit 1` est une version courte qui ne renvoie *aucune ligne* (et non
`NULL`) s'il y a moins de N valeurs. Pour le top-N par groupe, `row_number()` donne exactement N lignes
par groupe (arbitraire entre égalités), `dense_rank()` donne *tous* les ex æquo dans le top N. Pour une grande
table avec peu de groupes, `CROSS JOIN LATERAL (… order by … limit N)` est souvent plus rapide : avec un index sur
`(department_id, salary desc)`, il ne lit que N entrées d'index par groupe, alors que la version fenêtrée
numérote d'abord chaque ligne de la table.

**Exemple :**

```sql
-- 2e salaire distinct le plus élevé, sûr vis-à-vis de l'absence (la sous-requête scalaire renvoie NULL).
select (select salary
        from (select salary, dense_rank() over (order by salary desc) as r from employees) t
        where r = 2
        limit 1) as second_highest;

-- Top 3 des niveaux de salaire distincts par département (tous les ex æquo inclus).
select *
from (select e.*, dense_rank() over (partition by department_id order by salary desc) as r
      from employees e) t
where r <= 3;

-- Même idée avec LATERAL : exactement 3 lignes par département, adapté à l'index.
create index on employees (department_id, salary desc);
select d.name as department, top.name, top.salary
from departments d
cross join lateral (
    select e.name, e.salary
    from employees e
    where e.department_id = d.id
    order by e.salary desc
    limit 3
) top;
```

**Pourquoi c'est un piège :** se rabattre sur `limit 1 offset 1` ou `max(salary) where salary < max` et crier victoire — le premier échoue
sur les égalités et sur « moins de N », le second ne se généralise pas à N. Et `row_number()` pour un « top 3 » écarte
silencieusement le quatrième employé qui gagne exactement la même chose que le troisième.

#### Q14. Comment trouver et supprimer des lignes en double, et comment éviter qu'elles reviennent ? {#find-delete-duplicate-rows-stop}
**Réponse :** On les trouve avec `GROUP BY … HAVING count(*) > 1`. On les supprime en numérotant les lignes de chaque
groupe de doublons avec `row_number()` et en supprimant toutes les lignes sauf celle qu'on a décidé de garder (la plus ancienne,
la plus récente, la plus complète) — cette règle doit être explicite, c'est la vraie question métier. Si la table n'a pas de
clé exploitable, l'identifiant physique de ligne `ctid` de PostgreSQL identifie une ligne. Avant de supprimer, vérifiez ce qui
pointe vers les lignes condamnées : les clés étrangères des tables enfants doivent d'abord être redirigées vers la survivante. Enfin,
ajoutez la contrainte qui rend le problème impossible — un index unique (sur `lower(email)` si « identique » signifie
insensible à la casse) créé `CONCURRENTLY` ; sans lui, les doublons reviennent (S7).

**Exemple :**

```sql
-- 1. Trouver
select lower(email), count(*) from customers group by 1 having count(*) > 1;

-- 2. Supprimer, en gardant la ligne la plus ancienne de chaque groupe.
delete from customers c
using (select id,
              row_number() over (partition by lower(email) order by created_at, id) as rn
       from customers) d
where c.id = d.id and d.rn > 1;

-- 3. Prévenir
create unique index concurrently uq_customers_email on customers (lower(email));
```

**Pourquoi c'est un piège :** supprimer des doublons sans règle déterministe « laquelle survit » (`order by`
avec un départage unique) rend le résultat arbitraire — et sauter l'étape 3 signifie que la prochaine race condition
(deux inscriptions simultanées) recrée exactement le désordre que vous venez de nettoyer.

#### Q15. Qu'est-ce qu'une CTE, quand une CTE récursive est-elle l'outil adapté, et qu'est-ce qui a changé dans PostgreSQL 12 ? {#cte-recursive-cte-right-tool}
**Réponse :** Une CTE (`WITH name AS (…)`) nomme une sous-requête pour qu'une requête complexe se lise de haut en bas. Avant
PostgreSQL 12, toute CTE était une **barrière d'optimisation** — calculée une fois et matérialisée, sans que les filtres
extérieurs soient poussés à l'intérieur. Depuis la 12, une CTE sans effet de bord référencée une seule fois est **inlinée** comme une sous-requête,
et l'on choisit explicitement avec `AS MATERIALIZED` (forcer la barrière — utile quand la CTE est coûteuse et
référencée deux fois) ou `AS NOT MATERIALIZED`. Une CTE **récursive** est la réponse SQL aux hiérarchies et
aux graphes — organigrammes, arbres de catégories, nomenclatures, « tous les subordonnés de ce manager » : un membre d'ancrage
amorce le résultat, le membre récursif joint l'itération précédente à la table jusqu'à ce qu'aucune nouvelle ligne n'apparaisse.
Protégez-vous toujours des **cycles** (un tableau de chemin, ou `CYCLE` à partir de PostgreSQL 14) et préférez `UNION ALL`
(`UNION` dédoublonne à chaque itération, à un certain coût). Les CTE peuvent aussi contenir `INSERT/UPDATE/DELETE …
RETURNING`, ce qui permet de déplacer des lignes entre tables de façon atomique en une seule instruction.

**Exemple :**

```sql
-- Tous les subordonnés directs et indirects de l'employé 1, avec profondeur et garde anti-cycle.
with recursive tree as (
    select id, name, manager_id, 1 as depth, array[id] as path
    from employees where id = 1
  union all
    select e.id, e.name, e.manager_id, t.depth + 1, t.path || e.id
    from employees e
    join tree t on e.manager_id = t.id
    where e.id <> all (t.path)               -- s'arrêter si les données contiennent une boucle
)
select repeat('  ', depth - 1) || name as org_chart, depth
from tree order by path;

-- Archiver et supprimer en une seule instruction atomique.
with moved as (delete from orders where created_at < now() - interval '2 years' returning *)
insert into orders_archive select * from moved;
```

**Pourquoi c'est un piège :** « les CTE sont toujours matérialisées, c'est donc une astuce de performance » est du folklore d'avant 2019 ;
sur PostgreSQL 12+ c'est généralement l'inverse. Et une CTE récursive sur des données contenant un cycle (un
manager qui reporte à son propre subordonné) boucle indéfiniment — la garde fait partie de la réponse, pas d'un supplément.

#### Q16. Comment trouver des séquences consécutives — « utilisateurs connectés 3+ jours de suite » ou les trous d'une colonne id (« gaps and islands ») ? {#find-consecutive-sequences-users-logged}
**Réponse :** L'astuce des îlots : dans chaque partition, soustraire un `row_number()` de la valeur. Pour des valeurs
consécutives, la différence est **constante**, ce qui étiquette chaque îlot ; on groupe sur cette étiquette pour obtenir
début, fin et longueur. Cela fonctionne pour les dates (`date - integer` donne une date), les entiers et les timestamps tronqués
au jour. Pour lister les *trous*, on compare chaque ligne à la suivante avec `lead()` et on garde les lignes où
l'écart est supérieur à un. Dédoublonnez d'abord : deux connexions le même jour casseraient la
différence constante.

**Exemple :**

```sql
-- Séries de 3+ jours de connexion consécutifs par utilisateur.
with d as (select distinct user_id, login_date from logins),
g as (
    select user_id, login_date,
           login_date - (row_number() over (partition by user_id order by login_date))::int as island
    from d
)
select user_id, min(login_date) as streak_start, max(login_date) as streak_end, count(*) as days
from g
group by user_id, island
having count(*) >= 3
order by days desc;

-- Trous dans une séquence d'ids (1,2,3,7,8 -> trou 4..6).
select id + 1 as gap_start, next_id - 1 as gap_end
from (select id, lead(id) over (order by id) as next_id from tickets) t
where next_id - id > 1;
```

**Pourquoi c'est un piège :** oublier le `distinct` (jours en double) ou trier sur une colonne non unique rend l'arithmétique des
séries fausse sans aucune erreur. De plus, le « trou » dans une colonne id générée n'est généralement *pas* un bug
(les inserts annulés consomment des valeurs de séquence — S21).

#### Q17. `EXISTS` vs `IN` vs `JOIN` : comment écrire « clients sans commande » et « clients ayant acheté *tous* les produits d'une catégorie » ? {#exists-join-write-customers-orders}
**Réponse :** Une **semi-jointure** (« a au moins une ligne correspondante ») s'écrit de préférence avec `EXISTS` : il s'arrête à la
première correspondance et ne peut jamais multiplier les lignes. Une **anti-jointure** (« n'en a aucune ») s'écrit `NOT EXISTS` (ou `LEFT JOIN … WHERE
right.id IS NULL`) — jamais `NOT IN (sous-requête)`, qui casse avec `NULL` (Q10, S17). Un `JOIN` simple utilisé comme filtre renvoie un client une fois *par
commande correspondante*, et l'on finit par ajouter `DISTINCT` pour masquer le bug. Dans PostgreSQL moderne, `IN (sous-requête)` et `EXISTS` donnent
généralement le même plan de semi-jointure : choisissez selon la lisibilité et la sûreté vis-à-vis de `NULL`, et confirmez avec `EXPLAIN`. La **division
relationnelle** (« *tous* les éléments d'un ensemble ») se résout par comptage : joindre, filtrer sur l'ensemble, grouper par l'entité, et comparer le
nombre distinct à la taille de l'ensemble.

**Exemple :**

```sql
-- Semi-jointure : clients avec au moins une commande PAID (chaque client une fois).
select c.id, c.name from customers c
where exists (select 1 from orders o where o.customer_id = c.id and o.status = 'PAID');

-- Anti-jointure : clients n'ayant jamais commandé (sûr vis-à-vis de NULL).
select c.id, c.name from customers c
where not exists (select 1 from orders o where o.customer_id = c.id);

-- Division : clients ayant acheté TOUS les produits de la catégorie 5.
select o.customer_id
from orders o
join order_items i on i.order_id = o.id
join products p    on p.id = i.product_id
where p.category_id = 5
group by o.customer_id
having count(distinct p.id) = (select count(*) from products where category_id = 5);
```

**Pourquoi c'est un piège :** `select distinct c.* from customers c join orders o …` « marche » sur les données de démo puis
trie/dédoublonne des millions de lignes en production ; et la requête de division est fausse si l'on compte des lignes
au lieu de `count(distinct …)` — acheter deux fois le même produit suffirait à qualifier.

#### Q18. Comment construire un pivot ou un rapport conditionnel en un seul passage — `FILTER`, `CASE`, `ROLLUP` ? {#build-pivot-conditional-report-one}
**Réponse :** Au lieu d'exécuter une requête par métrique (ou de joindre cinq fois la même table à elle-même),
agrégez **une seule fois** et placez la condition *à l'intérieur* de l'agrégat : `count(*) FILTER (WHERE status =
'CANCELLED')` (syntaxe PostgreSQL ; `sum(case when … then … end)` est la forme portable). Un seul scan de la table
produit chaque colonne du rapport. `GROUPING SETS`, `ROLLUP` et `CUBE` ajoutent des lignes de sous-totaux et de total général
dans le même passage. Protégez les ratios contre la division par zéro avec `nullif(denominator, 0)`, et rappelez-vous que les
agrégats ignorent les `NULL` (Q10) — `avg(x) filter (…)` sur zéro ligne correspondante vaut `NULL`, pas `0`.

**Exemple :**

```sql
select date_trunc('month', created_at)::date                                   as month,
       count(*)                                                                as orders,
       count(*) filter (where status = 'CANCELLED')                            as cancelled,
       round(100.0 * count(*) filter (where status = 'CANCELLED')
                   / nullif(count(*), 0), 1)                                   as cancel_pct,
       sum(total) filter (where status = 'PAID')                               as paid_revenue
from orders
group by 1
order by 1;

-- Sous-totaux par pays et total général dans le même passage.
select coalesce(c.country, 'ALL') as country, coalesce(o.status, 'ALL') as status, count(*)
from orders o join customers c on c.id = o.customer_id
group by rollup (c.country, o.status);
```

**Pourquoi c'est un piège :** exécuter N requêtes `count(*)` séparées (ou N auto-jointures) multiplie les I/O par N et
produit des chiffres lus à des instants légèrement différents (Q25, S13) ; un agrégat conditionnel unique est à la fois plus rapide
et cohérent.

#### Q19. Montrez auto-jointures, sous-requêtes corrélées et « dernière ligne par groupe » — et comment éviter la ré-exécution par ligne. {#show-self-joins-correlated-subqueries}
**Réponse :** Une **auto-jointure** compare des lignes de la même table : « employés qui gagnent plus que leur manager »
joint `employees e` à `employees m` sur `m.id = e.manager_id`. Une **sous-requête corrélée** référence la ligne
externe et est conceptuellement ré-exécutée pour chacune d'elles (« au-dessus de la moyenne de leur département ») — lisible, mais
sur une grande table on la réécrit généralement en jointure avec un ensemble pré-agrégé ou en fonction de fenêtrage, de sorte que
l'agrégat est calculé une fois par groupe au lieu d'une fois par ligne. Pour **« dernière ligne par groupe »**, PostgreSQL propose
`DISTINCT ON`, qui garde la première ligne de chaque groupe selon `ORDER BY` — la forme la plus courte et généralement la plus rapide
(avec un index sur `(customer_id, created_at desc)` il peut parcourir l'index) ; l'alternative portable est `row_number() = 1`.

**Exemple :**

```sql
-- Auto-jointure : employés gagnant plus que leur manager.
select e.name, e.salary, m.name as manager, m.salary as manager_salary
from employees e join employees m on m.id = e.manager_id
where e.salary > m.salary;

-- Au-dessus de la moyenne de leur département : sous-requête corrélée vs fenêtre (un seul passage sur les données).
select name from employees e
where salary > (select avg(salary) from employees where department_id = e.department_id);

select name from (select name, salary, avg(salary) over (partition by department_id) as dept_avg
                  from employees) t
where salary > dept_avg;

-- Dernière commande de chaque client.
select distinct on (customer_id) customer_id, id as order_id, total, created_at
from orders
order by customer_id, created_at desc, id desc;
```

**Pourquoi c'est un piège :** avec `DISTINCT ON`, l'`ORDER BY` doit *commencer par* les expressions du `DISTINCT ON`, et
sans départage unique (`id desc`) deux commandes au même timestamp rendent la « dernière » arbitraire — un résultat
instable qui n'apparaît que lorsque les données sont importées en masse.

#### Q20. Écrivez un upsert, renvoyez la ligne affectée, et expliquez où `ON CONFLICT` et `MERGE` diffèrent. {#write-upsert-return-affected-row}
**Réponse :** `INSERT … ON CONFLICT (cols) DO UPDATE SET …` est le « insérer ou mettre à jour » atomique de PostgreSQL : l'index
unique arbitre la course, donc deux instructions concurrentes ne peuvent pas insérer toutes les deux (le bug même de S7). On utilise
`EXCLUDED.col` pour désigner la ligne proposée, et `RETURNING` pour récupérer la ligne finale (ou l'id généré)
sans seconde requête. `DO NOTHING` ignore silencieusement — et **ne renvoie alors aucune ligne** en cas de
conflit, donc « insérer si absent et me donner l'id » nécessite un petit repli `UNION ALL`. `MERGE` (PostgreSQL 15+)
est l'instruction multi-branches du standard SQL (`WHEN MATCHED … WHEN NOT MATCHED …`, y compris des branches `DELETE`)
adaptée à la synchronisation ensembliste depuis une table de staging, mais contrairement à `ON CONFLICT` elle ne
garantit pas l'insertion sous concurrence : un insert concurrent peut encore lever une violation d'unicité qu'il faut
rejouer.

**Exemple :**

```sql
-- Compteur atomique : insère le premier hit, incrémente ensuite, sans course lecture-puis-écriture.
insert into page_views (page_id, day, views)
values (7, current_date, 1)
on conflict (page_id, day) do update set views = page_views.views + 1
returning views;

-- « Insérer si absent, et donne-moi toujours l'id » (DO NOTHING ne renvoie rien en cas de conflit).
with ins as (
    insert into tags (name) values ('sql') on conflict (name) do nothing returning id
)
select id from ins
union all
select id from tags where name = 'sql'
limit 1;

-- MERGE (PG 15+) : synchroniser le stock depuis une table de staging en une instruction.
merge into stock s
using incoming i on s.sku = i.sku
when matched     then update set qty = s.qty + i.qty
when not matched then insert (sku, qty) values (i.sku, i.qty);
```

**Pourquoi c'est un piège :** `ON CONFLICT` consomme quand même une valeur de séquence à chaque tentative (d'où des trous),
une même instruction ne peut pas mettre à jour deux fois la même ligne cible (`cannot affect row a second time` quand l'entrée
contient des doublons), et `DO UPDATE` écrit toujours une nouvelle version de ligne même si rien n'a changé — ajoutez une
clause `WHERE` pour éviter les mises à jour sans effet sur les tables chaudes (bloat, S14).

### Indexation & plans de requête

#### Q21. Quels types d'index PostgreSQL offre-t-il au-delà du B-tree par défaut, et quand recourir à chacun ? {#index-types-postgresql-offer-beyond}
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

#### Q22. Pourquoi l'ordre des colonnes compte-t-il dans un index composite (multi-colonnes) ? {#column-order-matter-composite-multi}
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

#### Q23. Quand l'ajout d'un index peut-il dégrader les performances ? {#adding-index-make-performance-worse}
**Réponse :** Un index est une seconde structure que la base doit garder cohérente : il échange du **coût d'écriture et de
l'espace contre de la vitesse de lecture**, et l'échange n'est pas toujours rentable. Il nuit quand : (1) **la table est
très sollicitée en écriture** : chaque `INSERT`/`UPDATE`/`DELETE` doit mettre à jour chaque index (et un `UPDATE` d'une
colonne indexée empêche les mises à jour HOT de PostgreSQL), donc dix index rendent les écritures environ dix fois plus
coûteuses et génèrent plus de WAL et de travail de vacuum ; (2) **la colonne a une faible sélectivité** (un booléen ou un
`status` à 3 valeurs dont l'une représente 95 % des lignes) : le planificateur préfère à raison un balayage séquentiel,
car suivre un index vers la majorité de la table est plus lent que la lire dans l'ordre ; (3) **la table est petite** : elle
tient en quelques pages et un balayage coûte moins qu'une recherche par index ; (4) **l'index n'est jamais utilisé** (mauvais
ordre de colonnes, fonction appliquée à la colonne comme `WHERE lower(email) = ...` sans index d'expression, conversion
implicite, `LIKE '%x'` avec joker en tête), donc vous payez la maintenance pour rien ; (5) **il est redondant** (`(a)` à
côté de `(a, b)`) ; (6) **il gonfle la mémoire** : les index se disputent `shared_buffers`/le cache de pages avec les
données, et évincent des pages utiles. Remèdes : index partiels (`WHERE status = 'PENDING'`), colonnes couvrantes
`INCLUDE`, suppression des index inutilisés repérés par `pg_stat_user_indexes.idx_scan = 0`, et toujours valider par
`EXPLAIN (ANALYZE, BUFFERS)` avant et après (voir [Persistence Q24](persistence-sql-postgres.md#read-analyze-output-diagnose-slow)). En production, créez les
index avec `CREATE INDEX CONCURRENTLY` pour ne pas bloquer les écritures.

**Exemple :**

```sql
-- Index sur une colonne à 3 valeurs : le planificateur l'ignore pour la valeur courante.
CREATE INDEX idx_appt_status ON appointment(status);
EXPLAIN SELECT * FROM appointment WHERE status = 'CONFIRMED';   -- Seq Scan (95 % des lignes)

-- Mieux : n'indexer que les lignes rares et intéressantes.
CREATE INDEX CONCURRENTLY idx_appt_pending ON appointment(start_at) WHERE status = 'PENDING';

-- Trouver les index qui coûtent des écritures mais ne sont jamais lus :
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;
```

**Pourquoi c'est un piège :** « requête lente ? ajoutons un index » est un réflexe, et chaque index supplémentaire ralentit
silencieusement chaque écriture et chaque migration. Décidez d'après le plan d'exécution et le ratio lecture/écriture, pas
par habitude (voir aussi [Persistence Q22](persistence-sql-postgres.md#column-order-matter-composite-multi) sur l'ordre des colonnes d'un index composite).

#### Q24. Comment lisez-vous la sortie de `EXPLAIN ANALYZE` pour diagnostiquer une requête lente ? {#read-analyze-output-diagnose-slow}
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

```text
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

#### Q25. Nommez les niveaux d'isolation des transactions et les anomalies que chacun prévient. {#name-transaction-isolation-levels-anomalies}
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

#### Q26. Expliquez le locking optimiste vs pessimiste en termes de contention réelle, pas seulement de définitions. {#optimistic-pessimistic-locking-terms-contention}
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

#### Q27. Comment PostgreSQL peut-il lui-même servir de work queue avec `SELECT ... FOR UPDATE SKIP LOCKED`, et quelles en sont les limites ? {#postgresql-itself-act-queue-select}
**Réponse :** Plusieurs workers qui interrogent une table `jobs` traiteraient normalement soit la même ligne
deux fois, soit se bloqueraient mutuellement sur les locks de lignes. `FOR UPDATE SKIP LOCKED` fait en sorte que la requête de chaque worker
prenne les premières lignes que *personne d'autre ne détient actuellement* et saute silencieusement celles verrouillées, de sorte que N workers
réclament des lots disjoints en concurrence sans service de coordination. La bonne forme est
**claim-then-process** : dans une transaction courte, sélectionner et marquer les lignes (`status = 'RUNNING'`, un
timestamp `locked_at`/lease, un id de worker), commit, faire le travail lent *en dehors* de toute transaction,
puis marquer comme terminé. Garder le lock de ligne ouvert pendant tout le job immobiliserait une connexion et une
transaction (bloquant vacuum, S19), ce n'est donc pas un substitut. Comme le claim est commité, un
worker qui plante laisse une ligne bloquée en `RUNNING` — il faut un **reaper** qui remet en file les lignes dont le
lease a expiré, ce qui signifie que les jobs s'exécutent *au moins une fois* et que les handlers doivent être idempotents ([Messaging Q13](messaging-rabbitmq-kafka.md#consumer-idempotent-even-messaging-system)). Autres limites : l'ordre n'est qu'approximatif sous concurrence, il n'y a ni backoff de retry intégré,
ni dead-letter ni fan-out, le polling ajoute de la latence et de la charge (à atténuer avec `LISTEN/NOTIFY`), et
le débit plafonne bien en dessous d'un vrai broker. C'est un excellent choix pour des volumes modestes où
l'on veut le job et ses données métier dans la *même transaction* (un outbox léger, module
4 Q38) et un mauvais choix comme bus d'événements généraliste.

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

#### Q28. Comment empêcher deux requêtes concurrentes de réserver le même créneau de rendez-vous ? {#prevent-two-concurrent-requests-booking}
**Réponse :** L'invariant (« un seul rendez-vous confirmé par médecin et par créneau ») doit être garanti **par la base de
données**, car les vérifications applicatives (`if (!exists) insert`) sont des races check-then-act : deux requêtes voient
toutes deux le créneau libre et insèrent toutes deux. Options, de la plus simple et solide à la plus lourde : (1)
**Contrainte d'unicité** sur `(doctor_id, slot_start)` (un index unique partiel `WHERE status = 'CONFIRMED'` permet aux
lignes annulées de coexister) : le second `INSERT` échoue avec une violation d'unicité que vous traduisez en
`409 Conflict`. Aucun verrou, bonne montée en charge, et impossible à contourner par un bug dans un autre service. Pour des
rendez-vous de durée variable, utilisez une **contrainte d'exclusion** PostgreSQL
(`EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_at, end_at) WITH &&)`) qui rejette tout intervalle qui
chevauche. (2) **Verrou pessimiste** : `SELECT ... FROM slot WHERE id = ? FOR UPDATE` dans la transaction sérialise les
écrivains sur cette ligne ; simple à raisonner mais garde une connexion et peut provoquer des deadlocks ou des files
d'attente sur un créneau très demandé (`FOR UPDATE SKIP LOCKED`, `NOWAIT` aident). (3) **Verrou optimiste** : une colonne
`@Version` sur la ligne du créneau ; le `UPDATE ... WHERE version = ?` du perdant touche 0 ligne et Hibernate lève
`OptimisticLockException`, que vous traduisez en 409 ou rejouez. Idéal quand les conflits sont rares. (4) **Isolation
serializable** avec nouvel essai en cas d'échec de sérialisation : correct mais coûteux, avec une logique de reprise
partout. Associez la garde en base à une **clé d'idempotence** pour qu'une nouvelle tentative du client après un timeout
renvoie la même réservation plutôt qu'une seconde tentative (voir [Full Stack Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need)). Mettez en
cache la disponibilité pour la consultation si vous voulez, mais jamais le cache comme source de vérité de la décision de
réservation.

**Exemple :**

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE appointment ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_at, end_at) WITH &&)
  WHERE (status = 'CONFIRMED');
```

```java
@Transactional
public Appointment book(BookCommand c) {
    try {
        return repo.saveAndFlush(new Appointment(c.doctorId(), c.start(), c.end(), c.patientId()));
    } catch (DataIntegrityViolationException e) {          // violation d'unicité/d'exclusion de PostgreSQL
        throw new SlotAlreadyTakenException(c.doctorId(), c.start()); // -> 409 Conflict via @ControllerAdvice
    }
}
```

**Pourquoi c'est un piège :** `saveAndFlush` est important : avec un simple `save`, la violation n'apparaît qu'au commit,
hors de votre `try/catch`, et le client reçoit un 500. De plus, `SERIALIZABLE`/`REPEATABLE READ` n'aident pas pour un
`exists` applicatif en deux requêtes sauf si vous rejouez ; la contrainte est la réponse fiable (voir
[Persistence Q25](persistence-sql-postgres.md#name-transaction-isolation-levels-anomalies) pour les niveaux d'isolation et
[Persistence Q26](persistence-sql-postgres.md#optimistic-pessimistic-locking-terms-contention) pour verrou optimiste vs pessimiste ; la conception complète est dans
[System Design Q45](system-design.md#design-ticket-seat-booking-system)).

### ORM & Hibernate

#### Q29. Qu'est-ce que le problème des requêtes N+1, et citez deux façons de le corriger. {#n-1-query-problem-name}
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

#### Q30. Nommez les quatre états d'une entité Hibernate, avec un exemple d'usage pour chacun. {#name-four-hibernate-entity-states}
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
`merge()` écarte silencieusement cette écriture plus récente sans détection de conflit, à moins que `@Version` (Q26)
ne soit aussi en jeu pour l'attraper.

#### Q31. Pourquoi les inserts/updates générés par l'ORM sont-ils souvent lents en masse, et comment y remédier ? {#orm-generated-inserts-updates-often}
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

#### Q32. En quoi l'approche de persistance de MyBatis diffère-t-elle de celle de JPA/Hibernate, et quand cette différence est-elle le facteur décisif ? {#mybatis-approach-persistence-differ-jpa}
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

#### Q33. Que fait réellement `flush()` sur un persistence context, et en quoi diffère-t-il de `commit()` ? {#calling-flush-persistence-context-differ}
**Réponse :** `flush()` pousse immédiatement tous les changements en attente vers la base de données mais ne **commit** pas
la transaction — il synchronise simplement le persistence context (le cache de premier niveau)
avec la base de données plus tôt, ce qui est parfois nécessaire avant d'exécuter une requête qui doit voir
ces changements non commités (par ex. une requête native contournant le persistence context). `commit()`
termine la transaction, rendant les changements permanents (et, selon le niveau d'isolation, visibles
pour les autres transactions) — un flush sans commit peut encore être annulé.

**Exemple :**

```java
entityManager.persist(order);
entityManager.flush();       // l'INSERT est envoyé à la BD maintenant, mais la transaction est toujours ouverte

Integer count = (Integer) entityManager
    .createNativeQuery("select count(*) from orders where id = :id")
    .setParameter("id", order.getId())
    .getSingleResult();      // voit la ligne flushée, car une requête native contourne
                              // le cache de premier niveau et interroge directement la BD

// entityManager.getTransaction().rollback(); // encore entièrement réversible à ce stade —
                                                // l'INSERT flushé est annulé avec tout le reste
```

**Pourquoi c'est un piège :** les candidats confondent « la donnée a atteint la base » avec « la donnée est
permanente ». Flusher tôt est parfois nécessaire, mais un flush n'est pas un commit — le changement est
encore entièrement réversible tant que la transaction n'est pas réellement terminée.

### Connexions & topologie

#### Q34. Comment dimensionnez-vous un pool de connexions HikariCP, et quelle est l'erreur de dimensionnement courante ? {#size-hikaricp-connection-pool-common}
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

#### Q35. Comment configurez-vous et routez-vous en toute sécurité vers plusieurs data sources dans une même application Spring ? {#configure-safely-route-multiple-data}
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

#### Q36. Qu'est-ce qui casse quand on ajoute naïvement un read replica pour scaler les lectures ? {#breaks-naively-add-read-replica}
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

*Voir aussi :* [System Design Q21](system-design.md#read-own-writes-break-under) pour les stratégies read-your-own-writes à l'échelle de l'architecture.

### Schéma & modélisation

#### Q37. Quel est le processus sûr pour une migration de schéma sur une base de production, et quels outils la gèrent ? {#safe-process-schema-migration-production}
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

-- V2 : backfill par lots (voir Q31/S12), pas un seul UPDATE géant.
-- Déploiement applicatif : les lectures basculent vers email_normalized.

-- V3, une fois la bascule complète :
alter table users drop column email;
```

**Pourquoi c'est un piège :** la migration unique « évidente » — ajouter directement la colonne `NOT NULL` en une
étape — passe souvent sans problème sur une petite base de staging à faible charge, puis verrouille ou échoue
en production simplement parce que la production a des ordres de grandeur de lignes en plus et un trafic concurrent
que le staging n'a jamais eu ; le pattern en plusieurs étapes n'est pas une précaution excessive, c'est la seule version qui
passe à l'échelle réelle et à la concurrence de la production.

#### Q38. Quand une colonne doit-elle être `JSONB` plutôt qu'un ensemble de tables correctement normalisées ? {#column-jsonb-properly-normalized-set}
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

#### Q39. Soft deletes vs hard deletes — quel est le vrai compromis ? {#soft-deletes-hard-deletes-trade}
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

#### Q40. `bigint` auto-incrémenté, UUID aléatoire (v4) ou UUID ordonné dans le temps (v7) pour les clés primaires — comment choisir ? {#auto-increment-bigint-random-uuid}
**Réponse :** Chaque option optimise quelque chose de différent. Un **`bigint` identity/sequence** est petit (8 octets),
l'index est dense et les inserts vont toujours vers la page B-tree la plus à droite (excellente localité et comportement
de cache), et les jointures sont rapides ; les inconvénients sont que les ids sont devinables (attaques par énumération
si l'autorisation n'est pas correcte, [Spring Q41](spring-architecture.md#authorization-live-url-rules-method)), ils révèlent le volume (« nous avons 4 231 commandes »),
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
désactive le batching d'inserts JDBC, Q31). Ma recommandation par défaut : une clé primaire interne `bigint`
pour les jointures plus, si des identifiants visibles de l'extérieur sont requis, un id public aléatoire séparé (ou
UUIDv7 comme clé primaire quand les ids sont générés dans de nombreux services ou clients) ; éviter v4 comme chemin chaud d'insert
clustered sur de grandes tables, et décider une fois pour toutes — changer plus tard le type de clé primaire est
l'une des migrations les plus coûteuses qui soient.

**Exemple :**

```sql
create table orders (
    id         bigint generated always as identity primary key,  -- 8 octets, insertion locale, jointures internes
    public_id  uuid not null default uuidv7() unique,           -- exposé dans les URL/API (PG 18 ; avant : généré par l'application)
    created_at timestamptz not null default now()
);
-- 8 vs 16 octets : l'écart se répète dans chaque colonne FK et chaque index secondaire (100M lignes x 3 index ~ plusieurs Go)
```

**Pourquoi c'est un piège :** « les UUID sont mieux parce qu'ils sont modernes/distribués » ignore qu'une clé v4 aléatoire
transforme chaque insert en écriture de page aléatoire sur un gros index — sans conséquence à 1M de lignes, douloureux à 500M —
et que le type de clé est presque impossible à changer plus tard.

#### Q41. Concevez le schéma et la stratégie d'indexation d'une table de feed/événements à forte écriture, en append, censée atteindre des milliards de lignes. {#design-schema-indexing-strategy-high}
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

#### Q42. Concevez l'indexation d'un écran de recherche qui filtre les commandes par statut et date, retrouve les clients par e-mail sans tenir compte de la casse, et supporte la recherche textuelle « contient ». Quelles fonctionnalités d'index utilisez-vous ? {#design-indexing-search-screen-filters}
**Réponse :** C'est une question de boîte à outils : associer chaque forme de requête au plus petit index qui la sert, puisque chaque
index coûte du débit d'écriture, du disque et du travail de vacuum. (1) **B-tree composite** pour la liste
principale — colonnes d'égalité d'abord, colonne de plage/tri en dernier (Q22) : `(customer_id, status, created_at desc)`.
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
perd le chemin économique de HOT-update de PostgreSQL. Prouver chaque choix avec `EXPLAIN (ANALYZE, BUFFERS)` (Q24)
sur des données à l'échelle de la production plutôt qu'à l'intuition.

**Exemple :**

```sql
create index idx_orders_pending on orders (created_at) where status = 'PENDING';   -- partiel
create index idx_orders_list on orders (customer_id, status, created_at desc)
    include (total);                                                                 -- couvrant
create index idx_customers_email on customers (lower(email));                        -- expression
create extension if not exists pg_trgm;
create index idx_customers_name_trgm on customers using gin (name gin_trgm_ops);    -- LIKE '%term%'
create index concurrently idx_x on orders (created_at);                              -- ne bloque jamais les écritures
```

**Pourquoi c'est un piège :** répondre « ajouter un index sur chaque colonne filtrée » — chaque index taxe toutes les écritures,
et la mauvaise forme (mauvais ordre de colonnes, `lower()` différent, joker en tête) est silencieusement ignorée par le planner.

#### Q43. Quand le partitionnement de table est-il la bonne réponse dans PostgreSQL, et que vous coûte-t-il ? {#table-partitioning-right-answer-postgresql}
**Réponse :** Le partitionnement déclaratif (`PARTITION BY RANGE (created_at)`, ou `LIST`/`HASH`) découpe une
table logique en tables filles physiques. Il est rentable dans trois situations : la **rétention** (supprimer
ou détacher une ancienne partition est une opération de métadonnées instantanée, alors que `DELETE`-er 200 millions
d'anciennes lignes génère la même quantité de WAL, de dead tuples et de travail de vacuum — la table en append de
la Q41 est le cas d'école), le **partition pruning** (une requête avec un filtre sur la clé de partition ne
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
(Q42) et l'archivage sont plus simples. Si la rétention est la *seule* raison, le
`DROP PARTITION` d'une table partitionnée est l'argument le plus fort. Tester avec `EXPLAIN` que le pruning a réellement lieu
(`Subplans Removed`/seules les partitions pertinentes listées) et surveiller le nombre de lignes par partition pour repérer le skew.

**Exemple :**

```sql
create table events (
    id bigint generated always as identity, created_at timestamptz not null, payload jsonb,
    primary key (id, created_at)                        -- la PK doit inclure la clé de partition
) partition by range (created_at);
create table events_2026_10 partition of events for values from ('2026-10-01') to ('2026-11-01');
create table events_default partition of events default;

alter table events detach partition events_2026_01;   -- rétention instantanée, sans DELETE de 200M de lignes
drop table events_2026_01;

explain select * from events where created_at >= now() - interval '7 days';  -- seules les partitions récentes doivent apparaître
```

**Pourquoi c'est un piège :** partitionner « pour la performance » une table qui ne pose pas encore de problème, avec des requêtes qui ne
filtrent pas sur la clé de partition — on paie le coût de planification et on perd l'unicité globale sans bénéfice de pruning.

### Évolution & compromis

#### Q44. Comment ajoutez-vous en toute sécurité une colonne `NOT NULL` à une table de 50 millions de lignes sans aucune interruption ? {#safely-add-null-column-50}
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
en concurrence avec les opérations normales) ; (4) terminer par `SET NOT NULL` : depuis PostgreSQL 12, il évite le scan complet de la table lorsqu'un
`CHECK (col IS NOT NULL)` déjà validé prouve la règle, donc il est instantané ; puis supprimer le check devenu redondant.
Le code applicatif qui écrit toujours la nouvelle colonne doit être déployé *avant* l'étape 3, pour qu'aucun nouveau
`NULL` n'apparaisse pendant la validation de la contrainte. Le pattern
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

-- Étape 4 : PG12+ voit le CHECK validé et saute le scan ; on supprime ensuite le check redondant.
alter table orders alter column region set not null;
alter table orders drop constraint orders_region_not_null;
```

**Pourquoi c'est un piège :** la migration qui « marche simplement » dans un environnement de staging avec quelques milliers de
lignes et sans trafic concurrent est exactement celle qui verrouille la production pendant toute la durée d'une
validation de table complète — la différence n'apparaît qu'à l'échelle réelle de la production, ce qui est
précisément pourquoi cela doit être un pattern délibéré et testé plutôt que quelque chose découvert à la
dure pendant un déploiement.

#### Q45. Quand dénormalisez-vous délibérément, et comment maintenez-vous la cohérence de la copie dénormalisée ? {#deliberately-denormalize-keep-denormalized-copy}
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

#### Q46. Détaillez, étape par étape, l'optimisation d'une requête complexe et lente. {#optimizing-slow-complex-query-step}
**Réponse :** Suivez une boucle fixe et ne changez **qu'une chose à la fois**, en re-mesurant après chaque modification : (1) obtenir le vrai plan —
`EXPLAIN (ANALYZE, BUFFERS)` sur des données à l'échelle de la production (Q24) ; (2) trouver le nœud *dominant* (celui avec le plus de temps,
ou boucles × coût par boucle), pas le premier suspect venu ; (3) comparer estimations et valeurs réelles — un
grand écart signifie que le problème vient des statistiques, pas du SQL ; (4) corriger par ordre de coût et de sûreté croissants : rendre les
prédicats **sargables** (aucune fonction ni cast sur la colonne indexée), réduire les lignes tôt (filtrer, agréger
et `LIMIT` *avant* de joindre les tables larges), supprimer le travail par ligne (sous-requêtes corrélées), puis ajouter ou remodeler
**un index** (Q22, Q42), puis donner assez de `work_mem` au tri/hash, et seulement en dernier recours pré-calculer (table de
synthèse, vue matérialisée). Arrêtez-vous dès que l'objectif est atteint — chaque étape ci-dessous ajoute aussi de la complexité.

Le cas d'étude : *« top 10 des clients par chiffre d'affaires sur les 90 derniers jours, avec la date de leur commande la plus récente »* sur
2M de `customers`, 20M d'`orders` (2 ans), 80M d'`order_items`. Les chiffres sont **illustratifs** (typiques de ce
type de charge, pas un benchmark) — reproduisez-les sur vos données ; c'est l'allure des gains qui compte.

**Étape 0 — base de référence (≈ 38 s).**

```sql
select c.id, c.name,
       (select sum(oi.quantity * oi.unit_price)
        from orders o join order_items oi on oi.order_id = o.id
        where o.customer_id = c.id
          and date_trunc('day', o.created_at) >= current_date - 90
          and o.status <> 'CANCELLED')                    as revenue,
       (select max(o.created_at) from orders o where o.customer_id = c.id) as last_order_at
from customers c
where c.id in (select customer_id from orders
               where date_trunc('day', created_at) >= current_date - 90)
order by revenue desc nulls last
limit 10;
```

```text
Limit  (actual time=38112..38112 rows=10)
  ->  Sort (Sort Method: top-N heapsort)
        ->  Hash Semi Join (actual rows=612000)
              ->  Seq Scan on customers
              ->  Hash -> Seq Scan on orders   Filter: (date_trunc('day', created_at) >= ...)
                           Rows Removed by Filter: 17,540,000
        SubPlan 1  (actual time=0.041..0.052 rows=1 loops=612000)    <- ~31 s du total
        SubPlan 2  (actual time=0.004..0.005 rows=1 loops=612000)
Execution Time: 38125 ms
```

Lecture : le coût dominant est `SubPlan 1` avec **`loops=612000`** — un coût minuscule par ligne exécuté 612 000
fois — et le filtre enveloppe `created_at` dans `date_trunc`, donc aucun index sur cette colonne ne pouvait être utilisé.

**Étape 1 — rendre le prédicat sargable (≈ 35 s, pas encore de gros gain).** `date_trunc('day', created_at) >=
current_date - 90` est équivalent à `created_at >= current_date - 90`, avec la colonne laissée nue. Seule, cette modification économise peu (il n'y a toujours
pas d'index sur `created_at`) mais c'est le **prérequis** de l'étape 4 — une bonne leçon : certaines étapes ne
paient pas isolément.

**Étape 2 — supprimer les sous-requêtes par ligne : agréger une fois, puis joindre (≈ 6 s).**

```sql
with recent as (
    select o.customer_id,
           sum(oi.quantity * oi.unit_price) as revenue
    from orders o
    join order_items oi on oi.order_id = o.id
    where o.created_at >= current_date - 90
      and o.status <> 'CANCELLED'
    group by o.customer_id
)
select c.id, c.name, r.revenue
from recent r join customers c on c.id = r.customer_id
order by r.revenue desc
limit 10;
```

612 000 exécutions corrélées sont devenues une jointure de hachage et un agrégat de hachage : `Parallel Seq Scan on orders`
(2,4M de lignes conservées), `Hash Join` sur `order_items`, `HashAggregate`. La réécriture permet aussi au planner
d'abandonner le scan inutile de `customers`, et l'on ne joint `customers` que pour les lignes survivantes. **Vérifiez la sémantique**
lors d'une réécriture : `last_order_at` a été retiré de cette version volontairement — voir l'étape 3.

**Étape 3 — `LIMIT` avant la jointure large, ne chercher les compléments que pour les gagnants (≈ 5,5 s).**

```sql
with top as (
    select o.customer_id, sum(oi.quantity * oi.unit_price) as revenue
    from orders o join order_items oi on oi.order_id = o.id
    where o.created_at >= current_date - 90 and o.status <> 'CANCELLED'
    group by o.customer_id
    order by revenue desc
    limit 10                                           -- réduire à 10 lignes AVANT toute autre jointure
)
select c.id, c.name, t.revenue, lo.created_at as last_order_at
from top t
join customers c on c.id = t.customer_id
cross join lateral (select created_at from orders
                    where customer_id = c.id order by created_at desc limit 1) lo
order by t.revenue desc;
```

La « commande la plus récente » est désormais calculée pour 10 clients (10 recherches d'index sur `orders(customer_id,
created_at desc)`), pas 612 000, et elle conserve le sens d'origine (dernière commande *de tous les temps*).

**Étape 4 — index pour le filtre, couvrant ce que la requête lit (≈ 2,4 s).**

```sql
create index concurrently orders_recent_idx
    on orders (created_at) include (customer_id, status);   -- plage sargable + index-only scan
create index concurrently orders_cust_created_idx on orders (customer_id, created_at desc);
```

```text
->  Index Only Scan using orders_recent_idx on orders
      Index Cond: (created_at >= (CURRENT_DATE - 90))   Heap Fetches: 0
      Buffers: shared hit=9412 read=2216      (avant : read=1,380,000 par le Seq Scan)
```

La tranche de 90 jours est lue directement depuis l'index (`Heap Fetches: 0` exige un vacuum récent — Q42) au lieu de
scanner 20M de lignes. Raison de la forme : colonne de plage en premier car le seul prédicat d'index est une
plage ; `INCLUDE` garde `customer_id`/`status` hors de la clé de tri.

**Étape 5 — arrêter le spill et corriger l'estimation (≈ 1,5 s).**

```text
HashAggregate  Batches: 17  Memory Usage: 4145kB  Disk Usage: 381MB     <- spill sur disque
```

`work_mem` (4 Mo par défaut) est trop petit pour 600 000 groupes, donc l'agrégat de hachage écrit des lots sur disque.
Augmentez-le **uniquement pour ce rôle ou cette transaction** (`set local work_mem = '128MB'`), pas globalement ×
`max_connections`. Si le plan montre `rows=2400` estimé contre `2,460,000` réel après un chargement de données, lancez
`ANALYZE orders` (S22) avant de toucher à quoi que ce soit d'autre.

**Étape 6 — seulement si 1,5 s reste trop lent : pré-calculer (≈ 40 ms).**

```sql
create materialized view customer_revenue_daily as
select o.customer_id, o.created_at::date as day, sum(oi.quantity * oi.unit_price) as revenue
from orders o join order_items oi on oi.order_id = o.id
where o.status <> 'CANCELLED'
group by 1, 2;
create unique index on customer_revenue_daily (customer_id, day);       -- requis pour CONCURRENTLY
refresh materialized view concurrently customer_revenue_daily;           -- à planifier toutes les heures / chaque nuit
```

Le dashboard somme alors ≤ 90 petites lignes par client. Le prix : les données sont aussi fraîches que le dernier rafraîchissement et
vous possédez désormais un job de rafraîchissement (Q45 — dites comment la péremption est détectée).

| Étape | Changement | Temps | Pourquoi ça a aidé |
|---|---|---|---|
| 0 | référence | 38 s | 612k sous-plans corrélés, fonction sur la colonne |
| 1 | prédicat sargable | 35 s | simple prérequis |
| 2 | agréger une fois, joindre | 6 s | 612 000 exécutions → 1 agrégat de hachage |
| 3 | `LIMIT` d'abord, `LATERAL` pour les compléments | 5,5 s | moins de lignes dans chaque nœud suivant |
| 4 | index de plage couvrant | 2,4 s | scan de 20M de lignes → 2,4M d'entrées d'index |
| 5 | `work_mem` / `ANALYZE` | 1,5 s | pas de spill disque, bonne méthode de jointure |
| 6 | vue matérialisée | 0,04 s | pré-agrégé, au prix de la fraîcheur |

**Pourquoi c'est un piège :** le réflexe junior est « ajouter un index sur chaque colonne du `WHERE` » — ici cela n'aurait
presque rien changé, car le coût venait de 612 000 exécutions corrélées et d'une fonction enveloppant la
colonne. L'habitude senior est de lire d'abord le plan, de nommer le nœud dominant, et de ne changer qu'une variable à la
fois ; les mauvais réflexes tout aussi tentants sont `set enable_seqscan = off` en production, augmenter `work_mem`
globalement, ou s'arrêter à l'étape 6 avant d'avoir vérifié si l'étape 2 suffisait.

## 🎯 Scénarios réels

### S1. Une requête qui était rapide devient de plus en plus lente à mesure que la table grossit {#query-used-fast-has-become}
- **Symptômes :** La latence d'une requête précise a augmenté sur plusieurs mois proportionnellement à la croissance
  de la table, bien au-delà de ce que la seule croissance du nombre de lignes devrait provoquer.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Exécuter `EXPLAIN ANALYZE` (Q24) et vérifier la présence d'un `Seq Scan` là où un `Index Scan`
  serait attendu, ou un grand écart entre les nombres de lignes estimés et réels du planner
  (statistiques obsolètes).
- **Exemple :**

  ```text
  Seq Scan on orders (actual time=0.02..812.40 rows=1200000 loops=1)
    Filter: (status = 'PENDING')
  Planning Time: 0.10 ms
  Execution Time: 815.02 ms
  ```

  Aucun index n'existe sur `status`, donc chaque requête qui filtre dessus scanne toute la table — et ce
  scan devient linéairement plus lent à mesure que la table grossit.

- **Résolution :** Ajouter l'index manquant (en vérifiant l'ordre des colonnes pour les cas composites, Q22), ou exécuter
  `ANALYZE` pour rafraîchir les statistiques si le plan est simplement faux à cause de statistiques obsolètes, ou
  réécrire la requête si une fonction enveloppant la colonne filtrée empêche l'usage de l'index.
- **Prévention :** Mettre en place une revue des requêtes basée sur `EXPLAIN` pour les nouvelles requêtes de chemin chaud avant leur livraison,
  et surveiller les slow-query logs en continu plutôt que de découvrir la dégradation via les retours utilisateurs.

</details>

### S2. Un outil d'APM signale des dizaines de requêtes quasi identiques déclenchées pour un seul chargement de page {#apm-tool-flags-dozens-near}
- **Symptômes :** Une page qui liste 50 éléments déclenche 51+ requêtes en base — une pour la liste, et
  une par élément pour une collection associée.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** N+1 classique (Q29) — le confirmer en vérifiant le type de fetch de l'association de l'entité et
  si le code itère sur la collection et accède à une association lazy dans la boucle.
- **Exemple :**

  ```text
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

</details>

### S3. Deux transactions concurrentes se bloquent mutuellement (deadlock), et l'une est annulée par la base {#two-concurrent-transactions-deadlock-one}
- **Symptômes :** Postgres journalise une erreur `deadlock detected`, nommant les deux processus en conflit
  et les locks que chacun détenait en attendant l'autre ; une transaction est automatiquement annulée (rollback)
  pour briser le cycle.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le message de log nomme lui-même les requêtes exactes et les types de locks impliqués — la
  cause habituelle est deux transactions qui mettent à jour les deux mêmes lignes (ou tables) dans un ordre opposé (A
  puis B dans une transaction, B puis A dans une autre).
- **Exemple :**

  ```text
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

</details>

### S4. Les requêtes échouent avec l'erreur « too many connections » propre à la base, indépendamment de la taille du pool côté application {#requests-fail-database-own-too}
- **Symptômes :** Le pool HikariCP de l'application n'est pas épuisé (les métriques montrent de la marge), mais la
  base elle-même rejette les nouvelles connexions.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Comparer le `max_connections` du serveur de base à la *somme* de la taille de pool de chaque
  instance applicative, plus tous les autres clients (outils d'admin, autres services partageant
  la base) — une flotte d'instances chacune généreusement dimensionnée peut collectivement dépasser la
  limite réelle du serveur même si le pool d'aucune instance ne paraît saturé.
- **Exemple :**

  ```text
  FATAL: sorry, too many clients already
  ```

  ```text
  show max_connections; -- 100
  -- 12 instances applicatives x maximum-pool-size: 15 chacune = 180 connexions possibles,
  -- déjà au-dessus de la limite du serveur avant même qu'un outil d'admin ne se connecte.
  ```

- **Résolution :** Réduire la taille de pool par instance en suivant les conseils de dimensionnement de la Q34, ou introduire un
  connection pooler (PgBouncer) devant la base pour multiplexer de nombreuses connexions applicatives sur moins de
  connexions réelles vers la base.
- **Prévention :** Suivre le total des connexions sur toute la flotte comme métrique de premier ordre par rapport à la
  limite configurée de la base, pas seulement l'utilisation du pool par instance.

</details>

### S5. Une migration de schéma verrouille une table de production et provoque une brève interruption {#schema-migration-locks-production-table}
- **Symptômes :** L'étape de migration d'un déploiement provoque un pic de latence des requêtes ou des timeouts francs
  pendant toute la durée de la migration, sur une table soumise à un trafic actif de lecture/écriture.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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
  le pattern en plusieurs étapes de la Q44 pour tout ce qui exigerait autrement une réécriture ou un scan complet
  de la table.
- **Prévention :** Exiger que chaque migration sur une grande table en production indique explicitement quel
  lock elle prend et pour combien de temps, dans le cadre de la revue — et tester les migrations sur un
  jeu de données à l'échelle de la production en staging, pas seulement sur une base de dev vide ou petite, puisque la durée des locks
  croît avec la taille de la table.

</details>

### S6. Un utilisateur soumet un formulaire, est redirigé vers une page de confirmation, et constate que sa soumission est absente {#user-submits-form-redirected-confirmation}
- **Symptômes :** Intermittent, et spécifiquement lié aux flux écriture-puis-lecture-immédiate — le même
  utilisateur qui recharge un instant plus tard voit correctement les données.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Incohérence read-after-write classique d'une configuration naïve avec read replica (Q36) —
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

</details>

### S7. Deux requêtes quasi simultanées créent toutes deux une ligne pour ce qui devrait être une entité unique, produisant des doublons {#two-near-simultaneous-requests-both}
- **Symptômes :** Sous charge concurrente (par ex. un utilisateur qui double-clique sur soumettre, ou une requête rejouée
  en course avec l'originale), deux lignes existent pour ce que la logique métier supposait ne pouvoir être
  qu'une seule (deux comptes pour un email, deux commandes pour une clé d'idempotence).

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S8. `SELECT COUNT(*)` sur une grande table est étonnamment lent et apparaît comme une requête chaude {#select-count-large-table-unexpectedly}
- **Symptômes :** Un dashboard ou une fonctionnalité de pagination appelant `COUNT(*)` sur une table de plusieurs millions de lignes
  prend des secondes, ce qui est disproportionné par rapport à la simplicité apparente de la requête.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S9. Les échecs de locking optimiste explosent pendant une période de fort trafic précise {#optimistic-locking-failures-spike-sharply}
- **Symptômes :** Les taux d'`OptimisticLockException` (ou d'erreur de conflit de version équivalente) grimpent
  pendant une fenêtre de forte concurrence connue (une vente flash, un événement populaire), causant une vague de
  mises à jour échouées que l'application remonte comme erreurs visibles par l'utilisateur ou comme retries silencieux.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Cela confirme en pratique le point de la Q26 — le taux d'échec du locking optimiste augmente
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

</details>

### S10. Après un crash applicatif en pleine opération, la base est laissée dans un état incohérent {#after-application-crash-mid-operation}
- **Symptômes :** Une opération métier en plusieurs étapes (débiter le compte A, créditer le compte B) est trouvée
  partiellement appliquée après un crash — un côté a eu lieu, l'autre non.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S11. Les requêtes filtrant sur une colonne `JSONB` ralentissent à mesure que la table grossit, alors que la colonne est indexée {#queries-filtering-jsonb-column-get}
- **Symptômes :** Une requête comme `WHERE metadata @> '{"status": "active"}'` sur une colonne `JSONB`
  se dégrade avec la croissance de la table alors même qu'« il y a un index ».

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Vérifier le type réel de l'index — un simple index B-tree sur une colonne `JSONB` ne supporte
  que l'égalité sur la valeur JSON *entière*, pas l'inclusion (`@>`) ni les requêtes d'existence de clé ; seul
  un index GIN (Q21) accélère réellement ces opérateurs. L'existence d'un index B-tree sur la colonne
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

</details>

### S12. Un job batch nocturne qui met à jour des millions de lignes une par une commence à expirer ou à submerger la base {#nightly-batch-job-updates-millions}
- **Symptômes :** Un job batch qui boucle sur les lignes et émet un `UPDATE` par ligne prend
  de plus en plus de temps à mesure que le volume de données croît, et pendant son exécution les autres requêtes sur la même
  table ralentissent sensiblement.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les updates ligne par ligne dans une boucle (le pattern de la Q31, mais pour des updates plutôt que
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

</details>

### S13. Un rapport affiche parfois des chiffres qui ne concordent pas, uniquement sous activité d'écriture concurrente {#report-occasionally-shows-numbers-don}
- **Symptômes :** Un rapport multi-requêtes (par ex. la somme de valeurs de plusieurs tables qui devraient se réconcilier) est
  correct quand le système est inactif mais parfois incohérent quand il est généré pendant que des écritures ont lieu
  en concurrence.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Vérifier le niveau d'isolation sous lequel s'exécutent les requêtes du rapport — au niveau par défaut Read
  Committed (Q25), chaque instruction individuelle de la transaction du rapport voit les dernières données
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

</details>

### S14. Les tailles des tables et index ne cessent de croître alors que le nombre de lignes est à peu près stable {#table-index-sizes-keep-growing}
- **Symptômes :** L'utilisation disque d'une table fréquemment mise à jour grimpe régulièrement, de façon disproportionnée par rapport à
  son nombre réel de lignes vivantes (stable ou à croissance lente), et les performances des requêtes se dégradent en parallèle.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S15. Supprimer une ligne supprime de façon inattendue un grand nombre de lignes liées dans plusieurs tables {#deleting-one-row-unexpectedly-deletes}
- **Symptômes :** Supprimer ce qui ressemblait à une entité unique et isolée (par ex. supprimer un utilisateur)
  se propage en cascade en supprimant des commandes, des enregistrements de paiement ou un historique d'audit que l'équipe pensait
  préservés.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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
  généralement aussi le déclencheur pour introduire des soft deletes (Q39) plutôt que de les hard-delete
  du tout.
- **Prévention :** Traiter `ON DELETE CASCADE` comme une décision délibérée et revue pour chaque relation,
  pas comme un défaut adopté par commodité — documenter explicitement, pour chaque clé étrangère, ce qui doit
  arriver aux lignes filles quand le parent est supprimé.

</details>

### S16. Immédiatement après un déploiement incluant une migration de schéma, l'application se met à lever des erreurs sur une colonne manquante ou inattendue {#immediately-after-deployment-includes-schema}
- **Symptômes :** Des erreurs comme « column does not exist » ou un échec de mapping apparaissent juste après
  le déploiement, mais seulement sur certaines instances, ou seulement brièvement.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le déploiement de la migration et celui du code applicatif ne sont pas atomiques ensemble — pendant un
  déploiement rolling, d'anciennes instances applicatives (attendant l'ancien schéma) peuvent encore tourner
  sur une base déjà migrée vers le nouveau schéma, ou une migration a été exécutée
  *après* que le nouveau code applicatif s'attendait déjà à elle, exposant brièvement un trou.
- **Exemple :**

  ```text
  ERROR: column "region" of relation "orders" does not exist
  ```

  Une nouvelle instance applicative, déjà déployée et attendant `orders.region`, a commencé à recevoir
  du trafic avant que la migration ajoutant cette colonne ait réellement été exécutée sur la base — ou
  l'inverse : d'anciennes instances exécutant encore la version précédente s'étranglent sur une colonne renommée/supprimée
  par une migration déjà appliquée.

- **Résolution :** Réordonner strictement le déploiement pour que la migration se termine toujours complètement avant que
  tout nouveau code applicatif qui en dépend ne reçoive du trafic, et s'assurer que la migration
  elle-même est rétrocompatible avec l'*ancienne* version de l'application pendant toute la durée où d'anciennes instances
  tournent encore (c'est exactement pourquoi le pattern de migration en plusieurs étapes, additif d'abord, de la Q44
  compte — il est conçu pour que l'ancien comme le nouveau code fonctionnent avec l'état de schéma intermédiaire).
- **Prévention :** Ne jamais livrer une migration qui à la fois ajoute une exigence (une nouvelle colonne `NOT NULL`, une
  colonne renommée) et requiert le nouveau code dans la même étape atomique — toujours scinder en une migration
  additive et rétrocompatible d'abord, déployée et vérifiée, avant qu'une migration de nettoyage ultérieure ne supprime ce dont
  l'ancien code avait besoin.

</details>

### S17. Un rapport « clients qui n'ont jamais commandé » retourne soudainement zéro ligne {#customers-never-ordered-report-suddenly}
- **Symptômes :** Une requête marketing qui listait ~12 000 clients sans commande chaque semaine
  retourne maintenant un résultat vide. Personne n'a modifié la requête et il n'y a eu aucune erreur ; les nombres de clients
  et de commandes semblent normaux.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S18. Un feed à scroll infini et un export CSV ralentissent chaque semaine, et les utilisateurs voient des lignes répétées ou manquantes {#infinite-scroll-feed-csv-export}
- **Symptômes :** L'écran d'admin « audit events » et un export nocturne utilisent tous deux la pagination. Charger
  les dernières pages prend maintenant 8+ secondes et la base montre des pics CPU périodiques chaque fois qu'un
  crawler ou un export parcourt la liste. Par ailleurs, le fichier d'export contient certaines lignes en double et en
  manque d'autres.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S19. `ALTER TABLE` reste bloqué, les déploiements calent et l'app ralentit, avec des dizaines de sessions « idle in transaction » {#alter-table-hangs-deploys-stall}
- **Symptômes :** Une migration de routine attend indéfiniment et toute la table `orders` devient
  non réactive derrière elle. `pg_stat_activity` montre des connexions à l'état `idle in transaction`,
  certaines depuis des heures. L'utilisation du pool de connexions est élevée alors que le CPU et les I/O sont faibles, et le bloat de la table
  continue de croître (S14).

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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
  `commit`/`rollback` ([Spring Q18](spring-architecture.md#open-view-osiv-default-many) pour la variante OSIV).

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
  échouent vite au lieu de bloquer tout le monde (Q37). Vérifier que le nombre de sessions `idle in transaction`
  revient à ~0 sous charge.
- **Prévention :** Définir `idle_in_transaction_session_timeout` (par ex. 30 s) au niveau du rôle comme filet
  de sécurité, `lock_timeout` dans l'outillage de migration, alerter sur l'âge des transactions et sur le nombre de
  `idle in transaction`, et interdire les appels réseau dans les méthodes `@Transactional` en revue.

</details>

### S20. Deux workers traitent le même job en file, et parfois un worker reste bloqué à attendre l'autre {#two-workers-process-same-queued}
- **Symptômes :** Une flotte de workers basée sur une table `jobs` envoie parfois la même facture deux fois.
  Après l'ajout de workers, le débit s'améliore à peine et certains workers montrent de longues attentes, tandis que
  d'autres ne traitent rien.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Lire la requête de claim. Un simple `select ... where status = 'PENDING' limit 10`
  suivi d'un `update` est une course check-then-act : deux workers lisent les mêmes lignes avant que l'un
  les mette à jour. Ajouter `for update` sans `skip locked` corrige la double lecture mais fait
  *attendre* le second worker sur les locks de lignes du premier — sérialisant toute la flotte (Q27). Confirmer dans
  `pg_stat_activity` (`wait_event_type = 'Lock'`, en attente sur `transactionid`).
- **Exemple :**

  ```sql
  -- Course : les deux workers obtiennent les mêmes 10 ids.
  select id from jobs where status = 'PENDING' order by id limit 10;
  update jobs set status = 'RUNNING' where id = any(:ids);
  ```

- **Résolution :** Réclamer atomiquement avec `FOR UPDATE SKIP LOCKED` dans une seule instruction (voir
  Q27), commiter le claim, traiter en dehors de la transaction, et ajouter un reaper pour les leases expirés.
  Puisque la livraison est désormais at-least-once, rendre le handler idempotent en enregistrant l'id de la facture avec
  une contrainte d'unicité avant l'envoi. Vérifier avec un test qui lance 8 workers sur 10 000
  jobs et asserte que chaque id de job a été traité exactement une fois et que le temps total diminue avec
  davantage de workers.
- **Prévention :** Placer la requête de claim derrière une seule méthode de repository testée ; load-tester avec
  des workers concurrents avant d'ajouter le second ; à plus fort volume, passer à un vrai broker
  ([Messaging](messaging-rabbitmq-kafka.md)) plutôt que d'étendre les responsabilités de la table-queue.

</details>

### S21. Les inserts se mettent à échouer avec `duplicate key value violates unique constraint "orders_pkey"` après un import de données {#inserts-start-failing-duplicate-key}
- **Symptômes :** Après avoir restauré un sous-ensemble de la production en staging (ou chargé un CSV legacy),
  l'app échoue sur les premières nouvelles commandes : `ERROR: duplicate key value violates unique
  constraint "orders_pkey" — Key (id)=(10001) already exists`. Elle échoue par intermittence, puis
  réussit une fois que les ids « rattrapent » — mais seulement après plusieurs requêtes échouées.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S22. Un rapport qui prenait 2 secondes toute la semaine prend 20 minutes le lundi matin, sans aucun changement de code {#report-took-2-seconds-all}
- **Symptômes :** Après le chargement en masse du week-end (~20 millions de lignes importées dans `transactions`),
  la même requête de dashboard est soudainement 500x plus lente et sature le CPU. Un `EXPLAIN` d'un collègue quelques
  heures plus tard montre un plan rapide.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Comparer les lignes estimées vs réelles dans `EXPLAIN (ANALYZE)` (Q24). Ici le planner
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

</details>

### S23. Un rapport de chiffre d'affaires est soudain 3× trop élevé après qu'on a « juste ajouté une jointure » {#revenue-report-suddenly-3-too}
- **Symptômes :** La finance constate que le CA mensuel du dashboard ne correspond plus à l'export comptable. Le nombre de
  commandes semble aussi gonflé, mais uniquement pour les commandes ayant plusieurs lignes *et* plusieurs paiements.
  Aucune erreur, aucun test en échec.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** **Fan-out** de jointure. `orders` a été jointe à deux tables un-à-plusieurs indépendantes, donc chaque
  ligne de commande est répétée `lignes × paiements` fois avant l'exécution de `sum(total)`. On le prouve en comparant
  `count(*)` à `count(distinct o.id)` dans le résultat joint, ou en exécutant la même somme sans la nouvelle jointure.
- **Exemple :**

  ```sql
  -- commande 1 : 3 lignes x 2 paiements = 6 lignes, son total est donc ajouté 6 fois
  select sum(o.total)
  from orders o
  join order_items i on i.order_id = o.id
  join payments p    on p.order_id = o.id;
  ```

- **Résolution :** Agréger chaque côté « plusieurs » à une ligne par commande **avant** de joindre (ou utiliser
  `exists`/une sous-requête lateral quand on n'a besoin que d'un indicateur), pour que la jointure soit un-à-un :

  ```sql
  select sum(o.total)
  from orders o
  join (select order_id, sum(amount) as paid from payments group by order_id) p on p.order_id = o.id;
  ```

  Ne « corrigez » pas avec `sum(distinct o.total)` — deux commandes différentes de même total se fondraient en une seule.

- **Prévention :** Règle pratique : ne jamais joindre deux relations un-à-plusieurs au même niveau d'une requête qui
  agrège. Ajouter un test de réconciliation (`sum` du rapport == `sum` de la table de base) sur un jeu de test avec
  des enfants multiples.

</details>

### S24. Deux paiements concurrents réussissent tous les deux et le stock devient négatif (ou un solde perd une mise à jour) {#two-concurrent-checkouts-both-succeed}
- **Symptômes :** Sous charge, la quantité d'`inventory` finit à −3, ou le solde d'un portefeuille est inférieur à la somme de
  ses transactions. Cela ne se reproduit jamais en test mono-utilisateur, et aucune exception n'est journalisée.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un cycle lecture-modification-écriture au niveau Read Committed par défaut (Q25) : les deux transactions lisent
  `qty = 1`, passent toutes deux le test « stock suffisant » dans l'application, et écrivent toutes deux `qty = 0` (ou la seconde
  écrase la première). C'est une **mise à jour perdue** ; ni le niveau d'isolation ni `@Transactional` seuls ne l'empêchent,
  car rien n'a indiqué à la base que les deux lectures étaient liées.
- **Exemple :**

  ```sql
  -- T1 et T2 s'entrelacent :
  select qty from inventory where sku = 'A';       -- les deux voient 1
  update inventory set qty = 0 where sku = 'A';    -- les deux réussissent (la seconde écrase la première)
  ```

- **Résolution :** Choisir l'outil correct le moins coûteux : (a) **une instruction atomique** portant la condition —
  `update inventory set qty = qty - 1 where sku = 'A' and qty >= 1` puis vérifier le nombre de lignes affectées (S9) ;
  (b) `select … for update` pour sérialiser sur cette ligne quand il faut lire, calculer puis écrire ; (c)
  le locking optimiste `@Version` si la contention est faible (Q26) ; (d) `SERIALIZABLE` avec retry pour les invariants multi-lignes.
  Une contrainte `CHECK (qty >= 0)` est le filet de sécurité qui transforme la corruption silencieuse en erreur bruyante.

  ```sql
  alter table inventory add constraint qty_non_negative check (qty >= 0);
  ```

- **Prévention :** Considérer tout « lire un nombre, calculer en Java, le réécrire » comme un signal de revue ; ajouter un
  test de concurrence qui lance 50 décrémentations parallèles sur 10 unités de stock et vérifie que exactement 10 réussissent.

</details>

### S25. La barre de recherche est instantanée en staging et prend 12 s en production {#search-box-instant-staging-takes}
- **Symptômes :** La recherche de clients par e-mail ou par texte « contient » utilise 100 % d'un cœur CPU et expire.
  Il *existe* un index sur `email`, et `EXPLAIN` montre toujours un scan séquentiel.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** L'index existe mais la *forme du prédicat* ne peut pas l'utiliser (Q42) : `lower(email) = …` enveloppe la
  colonne dans une fonction, `ilike '%terme%'` a un joker en tête, et une colonne `varchar` comparée à un paramètre numérique
  force un cast implicite. Le staging a 20 000 lignes, donc le seq scan passe inaperçu.
- **Exemple :**

  ```sql
  explain analyze select * from customers where lower(email) = 'ann@example.com';
  --  Seq Scan on customers (actual time=0.03..4120 rows=1)   Rows Removed by Filter: 2,999,999

  explain analyze select * from customers where name ilike '%anderson%';
  --  Seq Scan on customers  Filter: (name ~~* '%anderson%')
  ```

- **Résolution :** Créer l'index qui correspond à l'*expression* et à l'*opérateur*, puis relancer `EXPLAIN` :

  ```sql
  create index concurrently idx_customers_email_lower on customers (lower(email));
  create extension if not exists pg_trgm;
  create index concurrently idx_customers_name_trgm on customers using gin (name gin_trgm_ops);
  ```

  Normaliser à l'écriture (stocker `email_normalized`) ou utiliser `citext` est une alternative pour le premier cas.

- **Prévention :** Charger des volumes réalistes en staging et passer les 10 formes de recherche les plus lentes attendues dans
  `EXPLAIN` lors de la revue ; alerter sur les scans séquentiels de grandes tables (croissance de `pg_stat_user_tables.seq_scan`).

</details>

### S26. Un job « supprimer les anciennes lignes » tourne pendant des heures, les réplicas prennent du retard, et la table ne rétrécit pas {#delete-old-rows-job-runs}
- **Symptômes :** Un job de rétention exécute `delete from events where created_at < now() - interval '90 days'`
  (≈ 150 millions de lignes). Le retard de réplication grimpe à plusieurs minutes, l'usage disque *augmente*, et les requêtes sur `events`
  ralentissent après le job — alors que le nombre de lignes a baissé.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un unique `DELETE` géant est une transaction énorme : il écrit chaque ligne dans le WAL (d'où le retard des
  réplicas et la croissance disque), détient des locks, et ne fait que *marquer* les lignes mortes — l'espace n'est pas rendu avant le passage du vacuum
  (S14), et le travail entre en concurrence avec l'application. Vérifier le retard dans `pg_stat_replication`, `n_dead_tup`, et l'âge de la
  transaction dans `pg_stat_activity`.
- **Exemple :**

  ```sql
  delete from events where created_at < now() - interval '90 days';   -- 150M de lignes, une seule transaction
  ```

- **Résolution :** À court terme : supprimer par **lots** avec une pause, chaque lot dans sa propre petite transaction, en
  s'appuyant sur un index sur `created_at` :

  ```sql
  delete from events where id in (
      select id from events where created_at < now() - interval '90 days' order by id limit 10000
  );  -- répéter jusqu'à 0 ligne ; pause entre les tours ; surveiller le retard des réplicas
  ```

  Vraie solution : **partitionner par temps** et supprimer des partitions entières (Q43) — une opération de métadonnées sans volume de WAL
  ni lignes mortes.

- **Prévention :** Concevoir la rétention avant que la table soit grosse : partitions temporelles + `drop`/`detach` planifié ;
  alerter sur le retard de réplication et l'âge des transactions ; ne jamais lancer de suppressions non bornées en heures ouvrées.

</details>

### S27. Hibernate journalise `firstResult/maxResults specified with collection fetch; applying in memory` {#hibernate-logs-firstresult-maxresults-specified}
- **Symptômes :** Un endpoint de liste paginée (`PageRequest.of(0, 20)`) sur des commandes avec leurs lignes s'est mis
  à consommer des gigaoctets de heap et à prendre plusieurs secondes, alors que la page n'affiche que 20 lignes. L'avertissement
  `HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory` figure dans le log.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le correctif N+1 de Q29 (`join fetch o.items`) combiné à la pagination. Une jointure sur une collection
  multiplie les lignes, donc un `LIMIT` SQL couperait au milieu d'une commande ; Hibernate **charge donc toutes les
  commandes correspondantes avec leurs lignes et pagine dans la JVM**. Aucun `LIMIT` n'apparaît dans le SQL généré —
  à confirmer avec les logs SQL.
- **Exemple :**

  ```java
  @Query("select o from Order o join fetch o.items where o.status = :s")
  Page<Order> findByStatus(String s, Pageable p);     // applying in memory
  ```

- **Résolution :** Deux requêtes. D'abord paginer les **ids** (ou les entités sans la collection) en SQL, puis charger
  les collections pour ces seuls ids :

  ```java
  List<Long> ids = em.createQuery(
      "select o.id from Order o where o.status = :s order by o.id", Long.class)
      .setParameter("s", status).setMaxResults(20).getResultList();   // vrai LIMIT 20

  List<Order> page = em.createQuery(
      "select distinct o from Order o join fetch o.items where o.id in :ids order by o.id", Order.class)
      .setParameter("ids", ids).getResultList();
  ```

  Alternatives : `@BatchSize` sur la collection (une requête supplémentaire par page, sans jointure), ou une projection DTO
  qui agrège en SQL (Q18).

- **Prévention :** Traiter l'avertissement `HHH90003004` comme un log bloquant le build dans les tests ; ne jamais combiner
  `join fetch` sur une collection avec `Pageable`.

</details>

### S28. Le rapport quotidien est décalé d'un jour autour de minuit, et à nouveau deux fois par an {#daily-report-off-one-around}
- **Symptômes :** Les « commandes par jour » d'hier changent quand le rapport est relancé depuis un autre serveur ou une autre
  région ; quelques commandes créées à 23h30 apparaissent le jour suivant ; les comptes sont faux les deux jours de l'année où
  l'heure change.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un décalage de fuseau horaire. `timestamp without time zone` stocke une heure murale sans signification
  attachée ; `created_at::date` et `date_trunc('day', …)` sur un `timestamptz` utilisent le fuseau de la **session**,
  donc la même requête renvoie des jours différents pour un serveur UTC et un serveur parisien. Les jours de changement d'heure, un
  « jour » dure 23 ou 25 heures, donc `created_at + interval '24 hours'` est aussi faux. Vérifier
  `show timezone;` dans la connexion de reporting et le type de la colonne.
- **Exemple :**

  ```sql
  select count(*) from orders where created_at::date = current_date - 1;   -- dépend du fuseau de session
  ```

- **Résolution :** Stocker les instants en **`timestamptz`** (toujours UTC en interne), et calculer les bornes de jour dans
  le fuseau métier *explicitement*, avec un intervalle semi-ouvert qui reste sargable :

  ```sql
  select count(*) from orders
  where created_at >= (date_trunc('day', now() at time zone 'Europe/Paris') - interval '1 day') at time zone 'Europe/Paris'
    and created_at <  (date_trunc('day', now() at time zone 'Europe/Paris'))                    at time zone 'Europe/Paris';
  ```

  Migrer les colonnes `timestamp` héritées avec `alter column … type timestamptz using created_at at time zone 'UTC'`
  (après avoir confirmé dans quel fuseau ces valeurs ont été écrites ; en migration par étapes, Q44).

- **Prévention :** Convention : `timestamptz` partout, JVM/BD en UTC, conversion uniquement en bordure ; utiliser
  `Instant`/`OffsetDateTime` plutôt que `LocalDateTime` dans les entités ; tester les bornes à 23:59, 00:00 et un jour de changement d'heure.

</details>

### S29. Les longs rapports sur le réplica de lecture sont annulés avec « conflict with recovery » {#long-reports-read-replica-get}
- **Symptômes :** Des requêtes analytiques qui tournent plusieurs minutes sur le réplica en streaming meurent parfois avec
  `ERROR: canceling statement due to conflict with recovery — User query might have needed to see row versions that must be removed`.
  La même requête réussit sur le primaire ou quand elle est relancée la nuit.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Sur le primaire, le vacuum a supprimé des versions de lignes mortes dont la requête longue du réplica
  avait encore besoin ; rejouer ce WAL sur le réplica casserait le snapshot de la requête, donc le standby doit
  choisir : mettre la réplication en pause (le retard grandit) ou annuler la requête. Après `max_standby_streaming_delay`
  (30 s par défaut) il annule. Voir `pg_stat_database_conflicts` sur le réplica.
- **Exemple :**

  ```sql
  select datname, confl_snapshot, confl_lock from pg_stat_database_conflicts;  -- sur le réplica
  ```

- **Résolution :** Choisir délibérément le compromis : (a) un **réplica analytique** dédié avec un grand
  `max_standby_streaming_delay` (accepter le retard là, garder le réplica HA strict) ; (b) `hot_standby_feedback = on`
  pour que le primaire retarde le vacuum sur ces lignes (accepter du bloat sur le primaire, S14) ; (c) raccourcir le rapport ou l'exécuter
  depuis une table pré-agrégée (Q46 étape 6). Ajouter une logique de retry sur le SQLSTATE `40001`/`40P01` pour les jobs en lecture seule.
- **Prévention :** Ne pas mélanger réplicas de bascule OLTP et longues requêtes de reporting sur le même nœud ; surveiller
  le retard de réplication et les compteurs de conflits ; fixer un budget de durée maximale par rapport.

</details>

### S30. La même requête prend 5 ms dans `psql` mais 4 s depuis l'application, seulement après un certain temps d'exécution {#same-query-takes-5-ms}
- **Symptômes :** `select * from orders where customer_id = ?` est rapide pour la plupart des clients. Après quelques
  requêtes par connexion, certains clients (ceux avec des millions de commandes) deviennent très lents depuis l'application Java, alors que
  le SQL identique collé dans `psql` reste rapide.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** **Requêtes préparées et plan générique.** Le driver JDBC bascule vers une requête préparée côté serveur
  après `prepareThreshold` (5 par défaut) exécutions ; PostgreSQL planifie alors avec le plan *générique* sans littéral après avoir
  essayé cinq plans personnalisés, en choisissant le plan meilleur *en moyenne*. Avec des données déséquilibrées (un client possède 40 % de la table), le plan
  générique peut être un plan nested-loop + index correct pour les petits clients et catastrophique pour le géant — ou l'inverse.
  `psql` colle un littéral, donc il obtient un plan personnalisé. Reproduire avec `prepare` et `explain (analyze) execute` :

  ```sql
  prepare q(bigint) as select * from orders where customer_id = $1;
  explain (analyze) execute q(42);        -- petit client
  explain (analyze) execute q(1);         -- le client géant ; comparer plan et durée
  ```

- **Résolution :** Pour les colonnes déséquilibrées, définir `plan_cache_mode = force_custom_plan` pour ce rôle/cette session (ou
  par instruction via `prepareThreshold=0` de pgJDBC), en acceptant plus de temps de planification ; ou donner de meilleures statistiques au planner
  (`alter table orders alter column customer_id set statistics 1000; analyze orders;`) et, si le
  déséquilibre est voulu, router les « gros » tenants vers un autre chemin de requête. Vérifier avec `auto_explain` que le plan
  en production correspond maintenant au plan rapide.
- **Prévention :** Inclure un cas de clé déséquilibrée (le plus gros tenant/client) dans les tests de charge ; journaliser les plans des
  requêtes lentes avec `auto_explain.log_min_duration` ; quand une requête est rapide à la main et lente depuis l'application, comparer
  les plans **personnalisé vs générique** avant d'incriminer le réseau ou le pool.

</details>

## 🗣️ Questions posées en entretien

Questions rapportées d'entretiens réels, regroupées par sujet. Chacune a une courte réponse type : approfondissez avec les questions et scénarios détaillés ci-dessus, et dites la réponse à voix haute.

### Performance & dépannage

#### R1. Une requête qui prenait 50 ms prend maintenant 10 secondes. Comment diagnostiquer ? {#query-used-take-50-ms}
**Réponse :** `EXPLAIN (ANALYZE, BUFFERS)` et comparaison avec l'ancien plan : seq scan au lieu d'index, mauvaises estimations de lignes, ordre de jointures modifié.

Vérifier statistiques périmées (`ANALYZE`), bloat de table/index, croissance des données, nouvelle valeur de paramètre (données déséquilibrées, generic plan), index supprimé/inutilisé, attentes de verrous (`pg_stat_activity`), ou requête ORM modifiée (N+1, `LIKE '%x'`, fonction sur colonne indexée).

Corriger à la racine : index, réécriture, statistiques, partitionnement.

#### R2. Le CPU de la base atteint 100 % aux heures de pointe. Quelles étapes ? {#database-cpu-reaches-100-during}
**Réponse :** Trouver les plus gros consommateurs avec `pg_stat_statements` (temps total, appels) et corriger les pires : index manquants, N+1, requêtes non bornées. Vérifier les rafales de connexions (tailles de pool, pgbouncer) et l'autovacuum. Puis réduire la charge : cache de lecture, réplicas, écritures en lot. Monter en puissance seulement une fois les requêtes saines.

#### R3. Comment identifier et résoudre un goulot d'étranglement de base de données ? {#identify-resolve-database-bottleneck}
**Réponse :** Le classer : CPU, E/S, mémoire (cache hit ratio), verrous ou connexions. Utiliser métriques, `pg_stat_statements`, `pg_locks`, slow-query log et `EXPLAIN`. Résoudre selon la classe : index/réécritures pour CPU et E/S, transactions courtes et ordre de verrouillage cohérent pour les verrous, pooling pour les connexions, puis réplicas/partitionnement/sharding. Vérifier par les percentiles de latence avant/après.

#### R4. Une table atteint des centaines de millions de lignes. Comment améliorer les performances ? {#table-has-grown-hundreds-millions}
**Réponse :** Indexer selon les vrais accès (composites, partiels, couvrants), pagination par keyset plutôt que `OFFSET`, **partitionner** par date/tenant pour élaguer ou supprimer les anciennes partitions, archiver les données froides, garder les stats à jour, régler l'autovacuum, `BRIN` pour les séries temporelles en append-only, pré-agréger les rapports lourds, et déporter l'analytique vers un réplica ou un entrepôt.

### Concurrence

#### R5. Deux transactions modifient la même ligne simultanément. Comment gérer la concurrence ? {#two-transactions-update-same-row}
**Réponse :** La base sérialise les écritures sur une ligne : la seconde attend le commit de la première. Pour éviter les *lost updates* sur lecture-modification-écriture : `UPDATE` atomique, `SELECT … FOR UPDATE`, `@Version` optimiste, ou `SERIALIZABLE`/`REPEATABLE READ` avec nouvel essai. Garder les transactions courtes et verrouiller dans un ordre cohérent pour éviter les deadlocks.

#### R6. Verrouillage optimiste ou pessimiste pour un système de stock ? Pourquoi ? {#optimistic-pessimistic-locking-inventory-system}
**Réponse :** Selon la contention. Peu de conflits (nombreux articles différents) : **optimiste** (`@Version`, nouvel essai), aucun verrou conservé, passe bien à l'échelle. Article très demandé (vente flash) : **pessimiste** (`FOR UPDATE`) ou un `UPDATE` gardé atomique `UPDATE stock SET qty = qty - :n WHERE id = :id AND qty >= :n`, souvent le meilleur des deux. Ne jamais vérifier le stock en Java puis écrire.

### JPA / Hibernate

#### R7. Qu'est-ce que le problème N+1 en Hibernate/JPA et comment le résoudre ? {#n-1-problem-hibernate-jpa}
**Réponse :** Une requête charge N parents, puis une requête supplémentaire par parent charge une association lazy (1 + N requêtes). Détecter avec les logs SQL ou un compteur de requêtes en test. Corriger avec `JOIN FETCH`, `@EntityGraph`, `@BatchSize`/`default_batch_fetch_size` ou une projection DTO. Attention à la pagination avec fetch de collection (utiliser deux requêtes).

#### R8. La table des rendez-vous contient des milliards de lignes. Comment garder requêtes et maintenance rapides ? {#appointments-table-has-billions-rows}
**Réponse :** Vérifiez d'abord que les index correspondent aux chemins d'accès (`(practitioner_id, start_at)` pour les agendas, `(patient_id, start_at)` pour l'historique d'un patient). Puis **partitionnez** : par plage sur `start_at` (mensuelle) quand la plupart des requêtes sont bornées dans le temps, pour pouvoir détacher et archiver les anciennes partitions au lieu de supprimer ligne par ligne, et pour que l'autovacuum travaille sur des tables plus petites. L'élagage de partitions n'a lieu que si la requête filtre sur la clé de partition. Les contraintes d'unicité et d'exclusion sur une table partitionnée doivent inclure la clé de partition, ce qui entre en conflit avec la règle d'absence de chevauchement sur une plage horaire ([Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)). Options : partitionner plutôt par hachage sur `practitioner_id` (les contraintes d'exclusion sur tables partitionnées exigent PostgreSQL 17+), ou garder une table plus petite des « rendez-vous à venir » portant la contrainte et déplacer les lignes passées vers une table d'historique partitionnée.

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q23. Quand l'ajout d'un index peut-il dégrader les performances ?
2. Q8. Quel est l'ordre d'exécution logique des clauses d'une requête SQL — et pourquoi ne peut-on pas filtrer sur un alias de `SELECT` dans `WHERE` ?
3. Q29. Qu'est-ce que le problème des requêtes N+1, et citez deux façons de le corriger.
4. Q39. Soft deletes vs hard deletes — quel est le vrai compromis ?
5. Q40. `bigint` auto-incrémenté, UUID aléatoire (v4) ou UUID ordonné dans le temps (v7) pour les clés primaires — comment choisir ?
6. Q45. Quand dénormalisez-vous délibérément, et comment maintenez-vous la cohérence de la copie dénormalisée ?
7. Q12. Expliquez les fonctions de fenêtrage : `row_number` vs `rank` vs `dense_rank`, totaux cumulés, `lag`, et le piège de la frame par défaut.
8. Q16. Comment trouver des séquences consécutives — « utilisateurs connectés 3+ jours de suite » (gaps and islands) ?
9. Q46. Détaillez, étape par étape, l'optimisation d'une requête complexe et lente.
10. S22. Un rapport qui prenait 2 secondes toute la semaine prend 20 minutes le lundi matin, sans aucun changement de code

## 📌 Cheat-sheet

### Couche de persistance Java (JPA / Hibernate)

*À retenir d'abord :* (1) N+1 est le bug de performance ORM n°1 ; (2) connaître les états d'entité ; (3) batcher les écritures en masse ; (4) ne jamais paginer directement un `join fetch`.

- **JPA vs JDBC vs MyBatis** — JPA = ORM complet (mappe objets et tables) ; JDBC = bas niveau, manuel ; MyBatis = vous écrivez le SQL, il fait le mapping. *Choisir selon le niveau de contrôle dont vous avez besoin sur le SQL exact.*
- **Problème N+1** — 1 requête pour les parents, puis 1 de plus par parent quand des collections lazy sont touchées dans une boucle (N+1 au total). *Corriger avec `JOIN FETCH`, `@EntityGraph` ou batch fetching, pas avec un `FetchType.EAGER` généralisé.*
- **États d'entité Hibernate** — transient (neuve, inconnue d'Hibernate) → persistent (managed, changements suivis automatiquement) → detached (changements non suivis) → removed. *`merge()` sur une entité detached peut écraser silencieusement des données plus récentes.*
- **Locking optimiste vs pessimiste** — optimiste = aucun lock détenu, conflit détecté à l'écriture (ex. colonne `@Version`) ; pessimiste = verrouiller la ligne d'avance. *L'optimiste gagne à faible contention ; le pessimiste gagne à forte contention sur les mêmes lignes chaudes (évite les tempêtes de retries).*
- **`@Transactional` multi-datasource** — une seule annotation ne couvre pas atomiquement deux bases sans JTA/XA (transactions distribuées). *Concevoir plutôt autour d'une source de vérité unique par écriture.*
- **Écritures en masse** — batcher inserts/updates (API de batch JDBC, `VALUES` multi-lignes, ou `COPY`) ; jamais ligne par ligne dans une boucle. *`hibernate.jdbc.batch_size` seul ne suffit pas sans `order_inserts`/`order_updates`.*
- **`join fetch` + `Pageable`** — Hibernate pagine en mémoire (avertissement `HHH90003004`). *Paginer les ids d'abord, puis charger les entités.*
- **Clés primaires** — `bigint` = compact et local à l'insertion ; UUIDv4 = splits de pages aléatoires (inserts lents) ; UUIDv7 = distribué *et* à peu près ordonné dans le temps. *`IDENTITY` désactive le batching d'inserts Hibernate.*

### Écrire du SQL correct

*À retenir d'abord :* (1) SQL exécute `FROM` avant `SELECT` ; (2) `NULL` signifie « inconnu », pas une valeur ; (3) préférer `UNION ALL` ; (4) utiliser `EXISTS`, jamais `NOT IN`, pour « absent d'une autre table ».

- **Ordre logique SQL** — `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`. *`WHERE` ne voit pas un alias de `SELECT` ; `HAVING` peut filtrer les agrégats car il s'exécute après le regroupement.*
- **`LEFT JOIN` + `WHERE` sur la table de droite** — le transforme en jointure interne. *Mettre la condition dans `ON` ; utiliser `WHERE right.id IS NULL` pour les anti-jointures (lignes sans correspondance).*
- **`UNION ALL` par défaut** — `UNION` ajoute une passe de déduplication par tri/hash. *Il peut aussi fusionner des lignes légitimement répétées.*
- **`NULL` signifie « inconnu »** — `= NULL` ne correspond jamais (utiliser `IS NULL`) ; `<>` écarte les lignes `NULL` ; `count(col)` ≠ `count(*)` (il ignore les `NULL`).

  ```sql
  WHERE x NOT IN (SELECT y FROM t)   -- ne retourne rien si un y est NULL
  WHERE NOT EXISTS (SELECT 1 FROM t WHERE t.y = x)   -- sûr
  ```

- **`NULL`, unicité et `NOT IN`** — `NOT IN (subquery avec NULL)` ne retourne rien (utiliser `NOT EXISTS`). *`UNIQUE` autorise de nombreux `NULL` (PG15 `NULLS NOT DISTINCT` change cela).*
- **Semi/anti-jointure** — `EXISTS` / `NOT EXISTS` (jamais `NOT IN`). *Un `JOIN` utilisé comme filtre duplique les lignes ; « pour tous » = `having count(distinct …) = (taille de l'ensemble)`.*
- **Fan-out de jointure** — deux jointures un-à-plusieurs multiplient les lignes. *Pré-agréger chaque côté ; `sum(distinct)` n'est pas un correctif.*
- **Fonctions de fenêtrage** — calculent sur des lignes liées sans les réduire. `row_number` (unique) / `rank` (trous après les ex æquo) / `dense_rank` (sans trou). *La frame par défaut avec `ORDER BY` est `RANGE … CURRENT ROW` (ex æquo inclus !) : écrire `rows unbounded preceding`. Impossible de filtrer dessus dans `WHERE`.*
- **Top-N par groupe / Nième valeur** — clarifier d'abord les égalités, puis `dense_rank`/`row_number` en sous-requête. *Pour les grandes tables avec peu de groupes : `LATERAL … limit N` + index composite.*
- **Dernière ligne par groupe** — `DISTINCT ON` garde une ligne par clé. *Exige un départage unique dans `ORDER BY`.*
- **Rapports en un passage** — `count(*) filter (where …)`, `rollup` (sous-totaux), `nullif` pour éviter la division par zéro dans les ratios.
- **CTE (requêtes `WITH`)** — PG12+ inline les CTE à usage unique (`MATERIALIZED` pour forcer une étape séparée). *CTE récursive = hiérarchie : exige ancre + `UNION ALL` + garde anti-cycle.*
- **Gaps and islands** — `valeur - row_number()` est constant par série de valeurs consécutives (îlots) ; `lead()` trouve les trous. *`distinct` d'abord.* *(avancé)*
- **Doublons** — `row_number() over (partition by clé order by …)` puis supprimer `rn > 1`. *Rediriger d'abord les FK (clés étrangères), puis ajouter un index unique `CONCURRENTLY`.*
- **Upsert** — `ON CONFLICT DO UPDATE … RETURNING` est sûr face aux courses. *`DO NOTHING` ne renvoie aucune ligne ; `MERGE` (PG15) n'empêche pas les courses d'unicité.*
- **Fuseaux horaires** — `timestamptz` + bornes de jour explicites dans le fuseau métier en intervalles semi-ouverts (`>= début AND < début_suivant`). *Le fuseau de session change `::date`.*

### Index et performance des requêtes

*À retenir d'abord :* (1) lire le plan avec `EXPLAIN ANALYZE` ; (2) indexer les colonnes filtrées et jointes ; (3) l'ordre des colonnes d'un index composite compte ; (4) statistiques obsolètes = mauvais plans.

- **`EXPLAIN ANALYZE`** — affiche le vrai plan avec les temps. *Surveiller un `Seq Scan` (lecture complète de la table) sur une grande table et les écarts lignes estimées vs réelles (stats obsolètes → lancer `ANALYZE`). Un `EXPLAIN` simple n'est qu'une estimation, il n'exécute jamais la requête.*
- **Types d'index Postgres** — B-tree (défaut, égalité/plage) · GIN (inclusion JSONB, plein texte, tableaux) · GiST (géométrique/chevauchement de plages) · index partiel (petit, sous-ensemble filtré).
- **Ordre des colonnes d'un index composite** — colonnes d'égalité/haute sélectivité d'abord. *Sinon l'index ne sert silencieusement pas la requête.*
- **Boîte à outils d'index** — composite (égalité d'abord, plage en dernier), partiel (sous-ensemble chaud), couvrant `INCLUDE` (l'index-only scan nécessite une visibility map à jour), d'expression (`lower(email)`), GIN trigram pour `LIKE '%x%'`. *Construire avec `CONCURRENTLY` ; supprimer les inutilisés.* *(avancé)*
- **JSONB** — correct pour des données éparses/variables. *Normaliser tout ce qui est fréquemment filtré, joint ou vérifié par contrainte.*
- **Pagination** — `OFFSET` coûte O(offset) et se décale sous les écritures concurrentes. *Utiliser keyset (`where (created_at, id) < (...)`) avec un index composite correspondant et un départage unique.*
- **Bascule de plan après un chargement en masse** — statistiques obsolètes. *`ANALYZE` à la fin des jobs batch ; statistiques étendues pour les colonnes corrélées ; comparer lignes estimées vs réelles.*
- **Plans génériques vs personnalisés** — rapide dans `psql` mais lent dans l'appli ? *Comparer plan personnalisé vs générique (`plan_cache_mode`).* *(avancé)*
- **Optimiser une requête, dans l'ordre** — vrai `EXPLAIN (ANALYZE, BUFFERS)` → nœud dominant (boucles × coût) → estimations vs réel → prédicat sargable (utilisable par un index) → agréger/`LIMIT` avant de joindre → supprimer les sous-requêtes par ligne → index → `work_mem`/`ANALYZE` → pré-calcul en dernier. *Un changement à la fois.*

### Transactions et concurrence

*À retenir d'abord :* (1) Read Committed est le défaut et autorise les mises à jour perdues ; (2) rendre atomique la lecture-modification-écriture ; (3) ne jamais garder une transaction ouverte pendant un appel à un service distant.

- **Niveaux d'isolation** — Read Committed (défaut, ne prévient que les dirty reads) < Repeatable Read (prévient aussi les non-repeatable/phantom reads dans Postgres) < Serializable (équivalent totalement série, plus de retries).
- **Mise à jour perdue** — deux sessions font lecture-modification-écriture sur la même ligne en Read Committed et l'une écrase l'autre. *Utiliser `update … where qty >= 1` atomique, `FOR UPDATE`, `@Version`, plus une contrainte `CHECK`.*
- **`FOR UPDATE SKIP LOCKED`** — transforme une table Postgres en work queue : claim court, traitement hors transaction, ajout d'un reaper de leases (libère les claims abandonnés). *At-least-once, donc handlers idempotents.* *(avancé)*
- **Sessions `idle in transaction`** — détiennent des locks et l'horizon de vacuum, donc font caler les migrations. *Définir `idle_in_transaction_session_timeout` et `lock_timeout` ; garder les appels distants hors des transactions.*
- **Dimensionnement HikariCP** — plus petit que ce que l'intuition suggère. *Le total des connexions sur toute la flotte doit tenir dans le `max_connections` de la base, pas seulement dans le pool d'une instance.*
- **Read replicas** — un routage naïf casse le read-after-write (on écrit, puis on lit une donnée périmée). *Épingler les lectures sensibles aux écritures sur le primary.*
- **Conflits de réplica** — `max_standby_streaming_delay` vs `hot_standby_feedback` arbitrent entre requêtes annulées et bloat du primary. *(avancé)*

### Changements de schéma et exploitation

*À retenir d'abord :* (1) jamais une seule étape bloquante sur une énorme table en production ; (2) additif d'abord, backfill, puis nettoyage ; (3) surveiller les dead tuples et les transactions longues.

- **Changements de schéma sans interruption** — additif/nullable d'abord → backfill → application/nettoyage. *Chaque étape doit être compatible avec l'ancien et le nouveau code applicatif.*
- **Grosses migrations** — `NOT VALID` + `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`, additif-puis-backfill-puis-nettoyage. *Jamais une seule étape bloquante sur une énorme table en production.*
- **`ON DELETE CASCADE`** — une décision délibérée par relation, pas un défaut. *Passer en revue toute la chaîne de cascade.*
- **Soft deletes** (un flag `deleted_at` au lieu de supprimer la ligne) — risque de filtres `deleted_at is null` oubliés et de contraintes d'unicité qui bloquent sur des lignes « supprimées ». *Limiter l'unicité aux lignes actives avec un index partiel.*
- **Bloat de table/index** — `n_dead_tup` (lignes mortes) qui croît malgré un `n_live_tup` stable signifie qu'autovacuum ne suit pas. *Régler les paramètres par table ou trouver la transaction de longue durée bloquante.*
- **Partitionnement** — rentable pour la rétention (drop partition) et le pruning (ignorer des partitions). *La PK doit inclure la clé de partition, les requêtes doivent filtrer dessus, créer les partitions à l'avance ; ne pas partitionner avant que ça fasse mal.*
- **Gros deletes** — les découper en lots ou supprimer des partitions. *Un seul `DELETE` géant = déluge de WAL (journal d'écriture anticipée), retard de réplicas, bloat.*
- **Séquences** — les ids explicites ne font pas avancer la séquence : `setval` après les imports. *Les trous dans les ids sont normaux.*
- **Index qui nuit** — chaque index ralentit les écritures et consomme de l'espace ; il peut aussi être ignoré (faible sélectivité, fonction sur la colonne, types différents). *Vérifiez `EXPLAIN (ANALYZE)` et `pg_stat_user_indexes` ; supprimez les index inutilisés.*
