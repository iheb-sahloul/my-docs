# Java Core & JVM

## 🟡 Pièges seniors

### Langage & types

#### Q1. Pourquoi `String` est-elle immuable, et qu'est-ce que le string pool ?
**Réponse :** Une fois créé, le stockage interne des caractères d'une `String` n'est jamais modifié — chaque
méthode « modifiante » (`concat`, `substring`, `replace`) retourne une nouvelle `String`. Cela apporte la
thread safety sans synchronisation (partage sûr entre threads), permet d'utiliser une `String` sans risque comme
clé de `HashMap` (son hash peut être mis en cache, calculé une fois et stocké dans l'objet — voir la discussion
sur la performance à la Q11), et rend possible le **string pool** — les chaînes littérales (et les chaînes
internées) sont dédupliquées dans un pool partagé, de sorte que `"abc" == "abc"` vaut `true` (même référence
poolée) alors que `new String("abc") == "abc"` vaut `false` (un objet distinct du heap contourne le pool sauf si
vous appelez `.intern()`). Une nuance historique à connaître : avant Java 7, le string pool vivait dans
PermGen, une région de métadonnées de taille fixe — appeler `.intern()` sur de nombreuses chaînes uniques à
l'exécution (par ex. interner chaque token parsé depuis une saisie utilisateur) pouvait épuiser PermGen et
faire planter la JVM avec `OutOfMemoryError: PermGen space`. Depuis Java 7 le pool a été déplacé dans le heap
ordinaire, donc le même mauvais usage aujourd'hui ne fait que gonfler l'usage du heap au lieu de se heurter à
un plafond dur et séparé — le problème est moindre qu'avant, mais « interner chaque chaîne que je croise » reste
une mauvaise habitude qui va à l'encontre de l'objectif du pool : dédupliquer un ensemble *borné* de littéraux
récurrents.

**Exemple :**
```java
String a = "hello";
String b = "hello";
String c = new String("hello");

System.out.println(a == b);           // true  — both resolve to the same pooled literal
System.out.println(a == c);           // false — c is a distinct heap object
System.out.println(a == c.intern());  // true  — intern() returns the pooled reference
```

**Pourquoi c'est un piège :** les candidats disent souvent « les chaînes sont poolées » de façon générale, sans
la réserve sur `new String(...)` — un recruteur enchaînera immédiatement avec exactement cette ligne pour voir
si la distinction est réellement comprise, et pas mémorisée comme un fait isolé.

#### Q2. Quel est le piège de `==` avec l'autoboxing sur `Integer` ?
**Réponse :** La JVM met en cache les `Integer` boxés de -128 à 127 (le cache interne de `Integer.valueOf`,
rempli à l'initialisation de la classe et garanti par la JLS, pas seulement un détail d'implémentation sur
lequel on ne pourrait pas compter), donc `Integer a = 100; Integer b = 100; a == b` vaut `true` — les deux
pointent vers le même objet en cache, conformément à la spec — alors que le code identique avec `200` au lieu de
`100` vaut `false`, car les valeurs hors de la plage du cache allouent à chaque fois un nouvel objet. C'est un
piège d'entretien classique précisément parce qu'il « marche » sur de petits exemples et échoue silencieusement
en production dès que les données réelles dépassent 127 — les fixtures de test et les données de démo utilisent
de façon disproportionnée de petits nombres (ids, quantités, scores dans un test unitaire), ce qui explique
exactement pourquoi ce bug survit à la code review et passe les tests avant de casser en production avec des
valeurs réelles. La correction est inconditionnelle : utiliser `.equals()` (ou unboxer en `int` et comparer des
primitives) pour comparer des types boxés, jamais `==` — il n'existe aucun seuil au-delà duquel `==` devient
« assez sûr ».

**Exemple :**
```java
Integer a = 100, b = 100;
Integer x = 200, y = 200;

System.out.println(a == b); // true  — both in the cached [-128, 127] range
System.out.println(x == y); // false — outside the cache, two distinct objects

// The actual fix, independent of the value:
System.out.println(a.equals(b)); // true
System.out.println(x.equals(y)); // true
System.out.println(a.intValue() == b.intValue()); // true — unboxed primitive compare
```

**Pourquoi c'est un piège :** c'est l'un des rares bugs Java qui relève d'un comportement *spécifié*, et non
d'une bizarrerie de la JVM — la JLS impose explicitement le cache de -128..127, ce qui signifie que compter sur
le fait que `==` « marche » dans cette plage n'est même pas un comportement indéfini sur lequel vous avez eu de
la chance ; il est garanti de continuer à marcher jusqu'à ce qu'une valeur réelle franchisse la frontière.

#### Q3. Qu'est-ce que le type erasure, et qu'est-ce que cela casse réellement ?
**Réponse :** L'information de type générique (`List<String>` vs `List<Integer>`) n'existe qu'à la compilation
pour le contrôle de types ; le compilateur l'efface vers des raw types (`List`) avec des casts insérés, donc à
l'exécution les deux ne sont que des `List`. Cela casse : la surcharge de deux méthodes qui ne diffèrent que par
le paramètre de type générique (`void f(List<String>)` et `void f(List<Integer>)` entrent en collision, même
erasure) ; la création d'un tableau générique (`new T[10]` ne compile pas, puisque la JVM a besoin d'un type de
composant concret au point d'allocation) ; et les vérifications `instanceof` contre un type paramétré
(`x instanceof List<String>` n'est pas autorisé — seulement `x instanceof List<?>`). Le mécanisme concret que
le compilateur utilise pour masquer une conséquence de l'erasure est la **bridge method** : lorsqu'une
sous-classe redéfinit une méthode générique avec un type plus spécifique
(`class IntBox extends Box<Integer> { void set(Integer v) { ... } }` redéfinissant
`void set(T v)`), le compilateur génère une bridge method synthétique `set(Object)` qui caste et
délègue à `set(Integer)`, car au niveau du bytecode la signature effacée de la superclasse est
`set(Object)` et il faut bien que quelque chose la satisfasse pour que le polymorphisme (virtual dispatch)
fonctionne correctement. C'est la même raison pour laquelle `List<String>.class` n'existe pas comme objet
distinct de `List<Integer>.class` — il n'y a qu'un seul `List.class` à l'exécution.

**Exemple :**
```java
class Box<T> {
    void set(T value) { }
}
class IntBox extends Box<Integer> {
    @Override void set(Integer value) { } // your source-level override
    // compiler also generates: void set(Object value) { set((Integer) value); }
    // — a synthetic bridge method, visible via IntBox.class.getDeclaredMethods()
}
```

**Pourquoi c'est un piège :** les candidats savent en général dire que l'erasure « supprime l'information de
type générique à l'exécution », mais peu savent expliquer le mécanisme de bridge method qui permet au
polymorphisme de continuer à fonctionner malgré cela — c'est la différence entre réciter le terme et comprendre
ce que le compilateur a dû faire.

#### Q4. Qu'apporte le compact canonical constructor d'un record que `@Data` de Lombok ne garantit pas structurellement ?
**Réponse :** Le compact constructor d'un record (`record Range(int lo, int hi) { Range { if (lo > hi)
throw new IllegalArgumentException(); } }`) exécute la validation *avant* l'affectation des champs, comme partie
intrinsèque de l'unique façon de construire le type — il n'y a ni setter, ni second constructeur, ni builder
basé sur la réflexion capable de le contourner, car les champs d'un record sont `private final` et il n'existe
qu'un seul chemin de constructeur canonique. `@Data` génère une classe mutable avec des setters par défaut ; on
peut toujours obtenir l'immutabilité avec Lombok (`@Value`), mais le record offre cette garantie comme une
fonctionnalité du langage imposée par le compilateur, et non comme une convention qu'un futur mainteneur peut
violer discrètement en ajoutant un setter ou un second constructeur qui saute la validation.

**Exemple :**
```java
record Range(int lo, int hi) {
    Range { // compact constructor — runs before field assignment
        if (lo > hi) throw new IllegalArgumentException("lo > hi");
    }
}

Range r = new Range(5, 1); // throws immediately — no way to construct an invalid Range

@Data
class LombokRange {
    private int lo, hi; // mutable — setLo(999) after construction bypasses any validation
                          // that only lived in a constructor
}
```

**Pourquoi c'est un piège :** « les records et les classes `@Data` sont à peu près la même chose, avec juste
moins de boilerplate » est le mauvais modèle mental — la garantie du record est structurelle (le compilateur
l'impose), alors que l'immutabilité de `@Data` (si tant est qu'on ait pensé à `@Value` à la place) est une
convention qu'un appel de setter ultérieur ou un framework basé sur la réflexion peut violer silencieusement.

#### Q5. Comment le pattern matching pour `switch` se combine-t-il avec les sealed types, et pourquoi est-ce important pour l'exhaustivité ?
**Réponse :** Depuis Java 21, `switch` peut faire du pattern-matching directement sur les sous-types permis d'un
sealed type : `switch (shape) { case Circle c -> ...; case Square s -> ...; case Triangle t -> ...; }`.
Comme `Shape` est `sealed permits Circle, Square, Triangle`, le compilateur connaît l'ensemble complet des
sous-types possibles et peut vérifier que chaque cas est traité *sans* branche `default` — si une nouvelle
forme est ajoutée à `permits` plus tard, chaque switch exhaustif sur `Shape` dans le codebase devient une
erreur de compilation au cas manquant, et non un trou à l'exécution. Cela transforme ce qui était un risque à
l'exécution (oublier de mettre à jour une chaîne de `instanceof`, ou une branche `default` dans un switch à
l'ancienne qui fait silencieusement la mauvaise chose pour un cas auquel personne n'a pensé) en une garantie à
la compilation. La version piège de cette question demande ce qui se passe si vous *ajoutez* une branche
`default` « au cas où » — cela jette entièrement la vérification d'exhaustivité, car le compilateur considère
désormais le switch comme complet, que chaque sous-type permis ait ou non son propre cas, de sorte qu'un
sous-type nouvellement ajouté tombe silencieusement dans `default` au lieu de faire échouer la compilation.

**Exemple :**
```java
sealed interface Shape permits Circle, Square, Triangle {}
record Circle(double r) implements Shape {}
record Square(double side) implements Shape {}
record Triangle(double base, double height) implements Shape {}

double area(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.r() * c.r();
        case Square s -> s.side() * s.side();
        case Triangle t -> 0.5 * t.base() * t.height();
        // no default needed — compiler proves every permitted subtype is handled
    };
}
// Adding `record Rectangle(...) implements Shape {}` to `permits` now makes
// this switch fail to compile until a Rectangle case is added.
```

**Pourquoi c'est un piège :** ajouter un `default -> throw new IllegalStateException()` défensif ressemble à
une bonne pratique, mais cela réintroduit silencieusement exactement le trou à l'exécution que les sealed types
+ le switch exhaustif ont été conçus pour éliminer à la compilation.

#### Q6. Où `Optional` aide-t-il, et où son usage dégrade-t-il le code ?
**Réponse :** `Optional<T>` a été conçu pour exactement une tâche : un *type de retour* qui dit « il peut ne pas
y avoir de résultat » afin que l'appelant ne puisse pas oublier de gérer l'absence. Il n'est pas destiné à
remplacer `null` partout. Mauvais usages que les seniors doivent savoir signaler : (1) comme **champ** ou **paramètre de méthode** — il n'est pas `Serializable`, ajoute une allocation et un troisième état (`null` *ou*
vide *ou* présent) à un type censé supprimer des états ; préférer la surcharge ou `@Nullable` ; (2) **`Optional.get()`
sans vérification** — il ne fait que déplacer la `NullPointerException` vers une
`NoSuchElementException`, donc préférer `orElseThrow(...)`, `ifPresentOrElse`, ou des chaînes
`map`/`flatMap` ; (3) **`orElse(expensive())`** — l'argument est évalué *de façon eager* que la valeur soit
présente ou non, donc tout ce qui a un coût ou un effet de bord (un appel DB, une création d'objet)
doit aller dans `orElseGet(() -> ...)`, qui est lazy ; (4) **`Optional<List<T>>`** — retourner plutôt une
collection vide, puisque « aucun élément » est déjà représentable ; (5) **`Optional.of(x)` avec un `x`
potentiellement null** lève immédiatement une exception — `ofNullable` est le pont depuis le code legacy nullable.
Souvenez-vous aussi qu'un retour `Optional` dans un hot path alloue, sauf si l'escape analysis le supprime, ce
qui compte dans des boucles serrées mais pas dans du code de service ordinaire.

**Exemple :**
```java
// Eager: loadDefaultFromDb() runs EVERY time, even when the user is present.
User u = repo.findById(id).orElse(loadDefaultFromDb());

// Lazy: only runs when the Optional is empty.
User u2 = repo.findById(id).orElseGet(() -> loadDefaultFromDb());

// Absence is an error here — say so, don't call get().
User u3 = repo.findById(id)
        .orElseThrow(() -> new NotFoundException("user " + id));

// Chain instead of if (opt.isPresent()) { ... opt.get() ... }
String city = repo.findById(id)
        .flatMap(User::address)      // address() returns Optional<Address>
        .map(Address::city)
        .orElse("unknown");
```

**Pourquoi c'est un piège :** les candidats disent « `Optional` évite la `NullPointerException` » puis écrivent
`opt.get()` — l'exception ne fait que changer de nom. La question `orElse` vs `orElseGet` est la relance
classique parce que la version eager est invisible jusqu'à ce que l'argument ait un effet de bord
(un insert en double, une requête lente à chaque requête).

#### Q7. Quelles sont les façons courantes dont un pipeline `Stream` tourne mal, même lorsqu'il compile et « marche » dans un test ?
**Réponse :** Cinq cas récurrents. (1) **Laziness** : les opérations intermédiaires (`map`, `filter`,
`peek`) ne font rien tant qu'une opération terminale ne s'exécute pas, donc un pipeline sans opération terminale
ne fait silencieusement rien, et `peek` est une aide au debug, pas un endroit pour de la logique (il peut être
entièrement sauté, par ex. par `count()` sur une source dimensionnée depuis Java 9). (2) **Usage unique** : un
`Stream` ne peut être parcouru qu'une fois ; une seconde opération terminale lève `IllegalStateException: stream has already
been operated upon or closed` — conserver plutôt un `Supplier<Stream<T>>` ou la collection source.
(3) **Effets de bord avec les parallel streams** : `forEach(list::add)` depuis un stream parallèle mute
une `ArrayList` non thread-safe depuis plusieurs threads — éléments perdus, `null`s ou
`ArrayIndexOutOfBoundsException` ; le bon outil est `collect(...)`/`toList()`, qui construit des conteneurs par
thread et les fusionne (et voir la Q21 pour comprendre pourquoi du travail bloquant dans un stream parallèle
affame le common pool). (4) **Les variantes de List diffèrent** : `Stream.toList()` (Java 16) retourne une
liste *non modifiable* qui accepte les `null`s ; `Collectors.toList()` retourne une `ArrayList` non spécifiée,
en pratique mutable ; `Collectors.toUnmodifiableList()` rejette les `null`s — le code qui appelle ensuite
`.add()` sur le résultat casse quand quelqu'un « modernise » l'un vers l'autre.
(5) **`Collectors.toMap` sur des clés dupliquées** lève `IllegalStateException: Duplicate key` sauf si
vous fournissez une merge function, et lève `NullPointerException` sur une valeur `null` — un bug qui
n'apparaît que lorsque les données de production contiennent enfin un doublon.

**Exemple :**
```java
// (3) Broken: ArrayList is not thread-safe, parallel forEach races on it.
List<Integer> out = new ArrayList<>();
IntStream.range(0, 100_000).parallel().forEach(out::add);   // size < 100000, or an exception

// Correct: let the stream collect.
List<Integer> ok = IntStream.range(0, 100_000).parallel().boxed().toList();

// (4) Surprise when a caller mutates the result:
List<String> a = Stream.of("x", "y").toList();
a.add("z");                                   // UnsupportedOperationException

// (5) Works in tests, throws the day two users share an email:
Map<String, User> byEmail = users.stream()
        .collect(Collectors.toMap(User::email, u -> u));               // Duplicate key!
Map<String, User> safe = users.stream()
        .collect(Collectors.toMap(User::email, u -> u, (first, second) -> first));
```

**Pourquoi c'est un piège :** chacun de ces cas passe un test sur le happy path avec des données petites et propres.
Les recruteurs utilisent `toMap` avec doublons et `forEach` parallèle précisément parce qu'ils montrent
si vous avez déjà débuggé des streams en production plutôt que seulement lu un tutoriel.

#### Q8. Pourquoi `double` est-il inadapté à l'argent, et quels sont les pièges de `BigDecimal` une fois qu'on change ?
**Réponse :** `double` est une virgule flottante binaire : `0.1` n'a pas de représentation exacte, donc
`0.1 + 0.2 == 0.30000000000000004` et les erreurs s'accumulent à travers les sommes, remises et lignes de taxe —
un centime d'écart çà et là, ce dont les équipes de réconciliation et les auditeurs se soucient *bel et bien*.
`BigDecimal` (ou des unités mineures entières dans un `long`, c'est-à-dire des centimes) est la solution, mais
il a ses propres pièges : (1)
**`new BigDecimal(0.1)`** capture la valeur exacte du *double* (`0.1000000000000000055…`) — construire
depuis une `String` ou avec `BigDecimal.valueOf(0.1)` ; (2) **`equals()` compare le scale**, donc
`new BigDecimal("2.0").equals(new BigDecimal("2.00"))` vaut `false` — utiliser `compareTo() == 0`, et
ne jamais utiliser `BigDecimal` comme clé de `HashMap` ou dans un `HashSet` sans normaliser le scale (Q11) ;
(3) **`divide()` sans `MathContext` ni scale** lève `ArithmeticException: Non-terminating
decimal expansion` sur `1/3` ; (4) **le mode d'arrondi est une règle métier**, pas une valeur par défaut — `HALF_UP`
est ce que la plupart des gens apprennent, `HALF_EVEN` (« arrondi du banquier ») est le standard comptable parce
qu'il ne biaise pas les sommes vers le haut — et l'arrondi doit avoir lieu au point *défini* (par ligne vs.
sur le total de facture donne des résultats différents par construction, donc à convenir avec le domaine) ; (5) le
scale de la devise est une donnée (`JPY` a 0 décimale, `KWD` en a 3), donc ne pas coder en dur `setScale(2)`.

**Exemple :**
```java
System.out.println(0.1 + 0.2);                                   // 0.30000000000000004
System.out.println(new BigDecimal(0.1));                         // 0.1000000000000000055511151231257827...
System.out.println(new BigDecimal("0.1").add(new BigDecimal("0.2"))); // 0.3

BigDecimal a = new BigDecimal("2.0"), b = new BigDecimal("2.00");
System.out.println(a.equals(b));         // false — different scale
System.out.println(a.compareTo(b) == 0); // true

BigDecimal.ONE.divide(new BigDecimal(3));                        // ArithmeticException
BigDecimal third = BigDecimal.ONE.divide(new BigDecimal(3), 2, RoundingMode.HALF_EVEN); // 0.33

// 3 items at 0.125 each, rounding rule matters:
new BigDecimal("0.125").setScale(2, RoundingMode.HALF_UP);       // 0.13
new BigDecimal("0.125").setScale(2, RoundingMode.HALF_EVEN);     // 0.12
```

**Pourquoi c'est un piège :** « utilisez `BigDecimal` » est la demi-réponse que tout le monde donne. Les relances —
`new BigDecimal(double)`, `equals` vs `compareTo`, et *quel* mode d'arrondi à *quelle* étape —
sont là où naissent réellement les bugs financiers.

### Exceptions & ressources

#### Q9. Que garantit réellement `try-with-resources`, et sur quelle interface repose-t-il ?
**Réponse :** Toute ressource implémentant `AutoCloseable` (ou `Closeable`, qui l'étend et
restreint `close()` à ne lever que `IOException`) déclarée dans les parenthèses du `try(...)` voit son
`close()` appelé automatiquement à la sortie du bloc — normale ou par exception — dans l'ordre **inverse**
de déclaration, sans avoir besoin d'un bloc `finally`. Si le bloc try et `close()` lèvent tous les deux une exception,
c'est celle du bloc try qui est propagée, et l'exception de `close()` lui est rattachée comme exception **suppressed** (récupérable via `getSuppressed()`), plutôt que l'une masque silencieusement
l'autre comme le fait souvent un `try/finally` écrit à la main — une version manuelle qui appelle
`close()` dans `finally` et laisse cet appel lever perdra entièrement l'exception d'origine si
`close()` lève aussi, ce qui est un bug réel et courant dans le code écrit avant Java 7.

**Exemple :**
```java
class Resource implements AutoCloseable {
    private final String name;
    Resource(String name) { this.name = name; System.out.println("open " + name); }
    @Override public void close() { System.out.println("close " + name); }
}

try (Resource r1 = new Resource("A"); Resource r2 = new Resource("B")) {
    System.out.println("using both");
}
// Output: open A, open B, using both, close B, close A — reverse declaration order.
```

**Pourquoi c'est un piège :** les candidats comprennent bien la partie « fermeture automatique » mais connaissent rarement le
mécanisme des exceptions suppressed, qui est exactement le détail qui compte lors du debug d'une
stack trace de production contenant une section « Suppressed: » qu'un lecteur a survolée.

#### Q10. Exceptions checked vs unchecked — quel est le véritable compromis de conception ?
**Réponse :** Les exceptions checked (sous-classes de `Exception` mais pas de `RuntimeException`) doivent être
déclarées ou attrapées — le compilateur force l'appelant à reconnaître un mode de défaillance spécifique et
récupérable (par ex. `IOException`). Les exceptions unchecked (`RuntimeException` et ses sous-classes)
n'exigent aucune déclaration et signalent typiquement des erreurs de programmation (`NullPointerException`,
`IllegalArgumentException`) dont on ne s'attend pas à ce que les appelants se remettent localement. Le
compromis en pratique : les exceptions checked documentent et imposent la gestion de conditions réellement
récupérables, mais surutilisées (ou utilisées pour des choses dont un appelant ne peut pas se remettre de
façon significative) elles poussent les équipes vers du boilerplate `catch (Exception e) {}` qui avale toute la valeur
de l'exception — c'est pourquoi la plupart des frameworks Java modernes (y compris la hiérarchie `DataAccessException` de Spring)
privilégient délibérément les exceptions unchecked et réservent les checked aux défaillances réellement récupérables
et exploitables par l'appelant. Un piège connexe à nommer explicitement : `catch (Exception e) {}`
(ou pire, `catch (Throwable t) {}`) avale aussi silencieusement les exceptions unchecked et même les
`Error` qui n'étaient jamais censées être attrapées, donc l'instinct « attrapons tout »
ne cache pas seulement le boilerplate des exceptions checked — il peut cacher un vrai bug ou même masquer une
`OutOfMemoryError` qui aurait dû faire planter le processus bruyamment.

**Exemple :**
```java
// Checked: caller is forced to decide how to handle a recoverable failure.
void readConfig() throws IOException {
    Files.readString(Path.of("config.yml"));
}

// The lazy "fix" that defeats the point of checked exceptions:
try {
    readConfig();
} catch (Exception e) {
    // swallows IOException *and* any RuntimeException *and* would even
    // catch an AssertionError if the catch clause used Throwable instead
}
```

**Pourquoi c'est un piège :** la « solution » à laquelle les candidats recourent sous la pression de l'entretien —
`catch (Exception e) {}` — est exactement l'anti-pattern que la question cherche à débusquer ; une réponse senior
explique pourquoi c'est pire que des exceptions checked ou unchecked bien utilisées.

### Collections

#### Q11. Décrivez ce qui se passe réellement dans `HashMap.put()` et `.get()`, et expliquez pourquoi un mauvais `hashCode()` est un vrai bug de performance.
**Réponse :** `put()` calcule `hashCode()`, le disperse avec une fonction de mix interne
(`h ^ (h >>> 16)`, pour replier les bits de poids fort dans les bits de poids faible afin que les tailles de table qui sont de petites puissances de
deux gardent une bonne distribution), et choisit un index de bucket à partir de ce hash modulo la capacité
de la table. Si le bucket est vide, l'entrée y va directement ; sinon, elle est ajoutée à la chaîne de collisions de ce
bucket (une liste chaînée, ou — depuis Java 8, dès qu'un bucket dépasse
`TREEIFY_THRESHOLD` (8) entrées *et* que la table a au moins `MIN_TREEIFY_CAPACITY` (64)
buckets — convertie en arbre rouge-noir équilibré indexé par hash puis par une comparaison de départage)
et comparée via `equals()` pour détecter les clés dupliquées. `get()` fait le même calcul de hash pour
sauter au bon bucket, puis le parcourt/le recherche — O(log n) dans un bucket treeifié, O(n) dans un
bucket en liste. L'arbre repasse aussi en liste à la suppression une fois que le bucket descend sous
`UNTREEIFY_THRESHOLD` (6), donc un bucket ne reste pas un arbre pour toujours s'il n'était qu'un
pic transitoire. Un `hashCode()` qui retourne la même valeur pour de nombreux objets différents (ou pire, une
constante) force chaque clé dans le même bucket, dégradant les lookups de O(1) en moyenne vers
O(log n), la treeification vous sauvant en partie — mais une violation du contrat `hashCode()`/`equals()`
(deux objets égaux avec des hashes différents) est pire que lente : elle produit silencieusement des entrées
*dupliquées* pour des clés logiquement égales, puisque `put()` ne trouve jamais l'existante à
écraser.

**Exemple :**
```java
class BadKey {
    final String id;
    BadKey(String id) { this.id = id; }

    @Override
    public boolean equals(Object o) {
        return o instanceof BadKey k && k.id.equals(id);
    }
    // hashCode() not overridden -> falls back to Object's identity hash.
    // equals() says two BadKeys with the same id are equal, but hashCode()
    // disagrees -> contract violation.
}

Map<BadKey, String> map = new HashMap<>();
map.put(new BadKey("42"), "first");
map.put(new BadKey("42"), "second"); // different identity hash -> different bucket
System.out.println(map.size()); // 2, not 1 — "duplicate" entries for an equal key
```

**Pourquoi c'est un piège :** les candidats récitent « redéfinissez `hashCode()` pour la performance » mais oublient qu'un
contrat `equals()`/`hashCode()` rompu n'est pas un ralentissement — c'est un bug de correction qui
duplique silencieusement les données.

#### Q12. Pourquoi un objet mutable avec un `hashCode()` basé sur ses champs est-il dangereux comme clé de `HashMap` ou élément de `HashSet` ?
**Réponse :** Une `HashMap`/`HashSet` range une entrée dans un bucket en utilisant le `hashCode()` de la clé *au
moment de l'insertion* et ne le recalcule jamais (Q11). Si un champ qui participe à `hashCode()` /
`equals()` est muté ensuite, l'entrée reste dans l'ancien bucket alors que chaque lookup ultérieur
hashe vers un *autre* — donc `contains()`, `get()` et `remove()` ratent tous un élément qui est
manifestement toujours dans la collection (l'itération le trouve encore). Rien ne lève d'exception : l'entrée est
simplement orpheline. C'est à la fois un bug de correction (l'élément « supprimé » est toujours là, un
`Set` accepte un doublon logique) et une fuite mémoire (l'orphelin ne peut plus jamais être supprimé par clé, donc
il vit aussi longtemps que la collection). Le même échec touche `TreeMap`/`TreeSet` quand le
champ muté participe à `compareTo()`, et il ne touche pas du tout les *valeurs* de `HashMap` — seules
les clés et les membres de set comptent. Les conceptions sûres sont : utiliser des clés immuables (un `record`, une `String`, un
`UUID`, ou l'id immuable de l'entité plutôt que l'entité entière), ou, si vous devez muter,
retirer l'élément d'abord, le muter, puis le réinsérer.

**Exemple :**
```java
class Session {
    final String id;
    String state = "OPEN";             // mutable, and used in hashCode()
    Session(String id) { this.id = id; }

    @Override public boolean equals(Object o) {
        return o instanceof Session s && s.id.equals(id) && s.state.equals(state);
    }
    @Override public int hashCode() { return Objects.hash(id, state); }
}

Set<Session> active = new HashSet<>();
Session s = new Session("a1");
active.add(s);

s.state = "CLOSED";                    // hashCode changes, bucket does not

System.out.println(active.contains(s)); // false — looks in the "CLOSED" bucket
System.out.println(active.remove(s));   // false — cannot be removed by key any more
System.out.println(active.size());      // 1     — still there, and now unreachable by lookup

// Fix: key on the immutable part only.
@Override public boolean equals(Object o) { return o instanceof Session s && s.id.equals(id); }
@Override public int hashCode() { return id.hashCode(); }
```

**Pourquoi c'est un piège :** la classe passe tous les tests unitaires qui construisent l'objet une fois et le recherchent
immédiatement — le bug n'apparaît que lorsque quelque chose mute l'objet *alors qu'il est dans une
collection hashée*, souvent loin de l'endroit où il a été inséré, et le symptôme (un élément « fantôme »)
apparaît bien après la mutation.

#### Q13. Qu'est-ce qui cause `ConcurrentModificationException`, et quelle est la bonne correction ?
**Réponse :** Les collections Java utilisent un itérateur fail-fast reposant sur un champ `modCount` ;
l'itérateur capture `modCount` à sa création et le vérifie à chaque `next()`. Modifier structurellement
la collection (add/remove, pas seulement mettre à jour une valeur via `set()`) en dehors de la propre méthode
`remove()` de l'itérateur — le plus souvent, en appelant `list.remove(x)` dans une
boucle `for (x : list)` — incrémente `modCount` et déclenche la vérification au prochain appel de `next()`. La
vérification n'est volontairement *pas* infaillible : c'est un détecteur au mieux, pas une garantie, donc une
boucle mono-thread remove-puis-break immédiat peut parfois passer sans lever d'exception,
c'est pourquoi « ça a marché dans mon test » n'est pas une preuve de correction ici. La bonne correction est
d'utiliser le propre `Iterator.remove()` de l'itérateur, ou `Collection.removeIf(predicate)`, ou (pour
l'accès concurrent) une collection concurrente comme `CopyOnWriteArrayList` ou `ConcurrentHashMap`,
qui ne lèvent pas cette exception parce qu'elles ne suivent pas les modifications de la même façon — elles
offrent plutôt une itération faiblement cohérente qui peut ou non refléter les changements concurrents, ce qui
est un compromis différent, pas un compromis strictement plus sûr.

**Exemple :**
```java
List<String> names = new ArrayList<>(List.of("Ann", "Bob", "Cid"));

for (String name : names) {
    if (name.equals("Bob")) {
        names.remove(name); // throws ConcurrentModificationException on next()
    }
}

// Fix: drive removal through the iterator itself.
Iterator<String> it = names.iterator();
while (it.hasNext()) {
    if (it.next().equals("Bob")) {
        it.remove(); // safe — updates modCount through the same iterator
    }
}
// Or, more idiomatically:
names.removeIf(n -> n.equals("Bob"));
```

**Pourquoi c'est un piège :** il est facile de « corriger » cela en enveloppant la boucle dans un `try/catch` ou en la convertissant
en boucle par index qui saute un élément après la suppression — les deux cachent un vrai bug au lieu de
le corriger (la version par index saute silencieusement l'élément qui suit celui supprimé).

#### Q14. Concevez un cache LRU thread-safe et borné from scratch. Quels sont les vrais compromis ?
**Réponse :** Une `LinkedHashMap` en mode access-order (`new LinkedHashMap<>(cap, 0.75f, true)`) avec
`removeEldestEntry` redéfini pour évincer au-delà d'un seuil de taille vous donne la sémantique LRU presque
gratuitement, car le mode access-order re-lie une entrée en queue de la liste doublement chaînée interne
à chaque `get()`, si bien que la tête est toujours l'entrée la moins récemment utilisée — mais elle n'est pas thread-safe
par elle-même, donc on enveloppe l'accès dans un lock unique (`synchronized` ou un `ReentrantReadWriteLock`) ou
on utilise `Collections.synchronizedMap`. Le compromis à ce stade est un lock global unique qui sérialise
chaque lecture, ce qui convient pour une contention faible à modérée mais devient le goulot d'étranglement sous forte
concurrence, puisque même un simple `get()` mute la liste chaînée interne (pour enregistrer l'accès)
et ne peut donc pas être une pure lecture concurrente. Pour un meilleur débit, la vraie réponse est de
segmenter le cache (striped locks, comme l'ancien interne de `ConcurrentHashMap`) ou de recourir à une
bibliothèque dédiée (Caffeine) qui implémente un LRU/LFU approximatif avec des lectures lock-free via un journal
d'accès basé sur un ring buffer et une éviction par échantillonnage — à ce stade vous échangez l'ordre LRU parfait
contre de la concurrence, ce qui est presque toujours le bon compromis pour un cache de production. Le
signal recherché en entretien n'est pas de réciter les internes de Caffeine ; c'est de reconnaître *pourquoi* un LRU naïf et une forte
concurrence sont en tension (chaque lecture est aussi une écriture dans la structure d'ordre).

**Exemple :**
```java
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;

    LruCache(int capacity) {
        super(capacity, 0.75f, true); // true = access-order, not insertion-order
        this.capacity = capacity;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity; // evict the head once we exceed capacity
    }

    // Not thread-safe on its own — every public method must go through a lock:
    synchronized V getSafe(K key) { return get(key); }
    synchronized void putSafe(K key, V value) { put(key, value); }
}
```

**Pourquoi c'est un piège :** les candidats s'arrêtent souvent à « utiliser `LinkedHashMap` avec `removeEldestEntry` » comme
si cela répondait à lui seul à « thread-safe » — la question demandait explicitement du thread-safe, et la
solution naïve du lock partout est elle-même l'amorce de la relance sur les compromis de concurrence.

### Concurrence & modèle mémoire

#### Q15. Quelle est la vraie différence entre `synchronized` et `volatile` ?
**Réponse :** `synchronized` fournit l'exclusion mutuelle (un seul thread exécute le bloc à la
fois) **et** une arête happens-before : tout ce qu'un thread a fait avant de relâcher un lock est visible
pour le thread suivant qui acquiert ce même lock, y compris les écritures simples (non volatile) faites
plus tôt dans le bloc. `volatile` ne fournit que *la moitié visibilité* de cela — chaque lecture d'un
champ volatile voit l'écriture la plus récente qui y a été faite, à travers les threads, et la JVM ne peut pas
réordonner d'autres opérations mémoire de part et d'autre d'une lecture/écriture volatile — sans exclusion mutuelle ; deux
threads peuvent encore se disputer pour incrémenter un `volatile int` et perdre une mise à jour, car `i++` est un
read-modify-write qui n'est pas atomique même quand le champ est volatile. Le piège senior consiste à les traiter
comme interchangeables : utiliser `volatile` pour un simple flag ou une référence quand on veut de la visibilité
sans contention (un flag d'arrêt, une référence d'instance en double-checked locking — voir Q19), et
`synchronized` (ou un `Lock` explicite, ou une classe atomique) quand il faut protéger un invariant en plusieurs
étapes, c'est-à-dire lorsque plus d'un champ/opération doit être observé ou mis à jour comme un tout.

**Exemple :**
```java
class Counter {
    private volatile int count = 0; // visibility only — no atomicity

    void increment() {
        count++; // read, add, write — three steps, not one; a lost update is possible
    }
}

class SafeCounter {
    private int count = 0; // plain field is fine — synchronized supplies visibility too

    synchronized void increment() {
        count++; // mutual exclusion makes the three steps effectively atomic
    }
}
```
Deux threads appelant `Counter.increment()` 100 000 fois chacun peuvent terminer avec un total nettement
inférieur à 200 000 — `volatile` garantit que chaque thread finit par voir la dernière valeur, pas qu'aucun
autre thread ne s'intercale entre la lecture et l'écriture.

**Pourquoi c'est un piège :** « volatile rend thread-safe » est la réponse fausse la plus courante à
cette question — volatile ne supprime que les bugs de lecture périmée, il ne fait rien contre les race conditions sur
les opérations composées.

#### Q16. Qu'est-ce que la « safe publication » dans le Java Memory Model, et pourquoi un autre thread peut-il voir un objet à moitié construit ?
**Réponse :** Sans arête happens-before entre le thread qui construit un objet et le
thread qui lit la référence, le JMM permet au lecteur de voir la *référence* comme non nulle alors que
certains *champs de l'objet contiennent encore leurs valeurs par défaut* — le compilateur et le CPU sont libres de
réordonner les écritures de champs dans le constructeur par rapport à l'écriture de publication vers la variable partagée.
« Safe publication » signifie transmettre la référence via quelque chose qui établit un
happens-before : un initialiseur `static`, un champ `volatile` ou `AtomicReference`, un champ `final`
d'un objet correctement construit, un lock (un bloc `synchronized` ou un `Lock` utilisé par
*à la fois* l'écrivain et le lecteur), ou une collection concurrente / `BlockingQueue`. Les champs `final` bénéficient d'une
garantie spéciale — une fois le constructeur terminé, tout thread qui voit la référence voit aussi
les valeurs correctes de ses champs `final` (et de tout ce qui n'est accessible que par eux) même
à travers une data race — mais seulement si `this` ne *s'échappe* pas pendant la construction (enregistrer un
listener, démarrer un thread, ou stocker `this` dans un static depuis le constructeur donne
aux autres threads un objet partiellement construit). C'est la même règle de visibilité sur laquelle s'appuient la Q19
pour le double-checked locking et la Q15 pour `volatile` ; sur x86 l'anomalie est rare à observer, ce qui est
exactement pourquoi le bug survit aux tests et apparaît sur des serveurs ARM.

**Exemple :**
```java
class Config {
    int timeout;                         // non-final, non-volatile
    Config(int timeout) { this.timeout = timeout; }
}

class Holder {
    static Config config;                // racy publication: no volatile, no lock

    static void init()  { config = new Config(30); }
    static int  read()  { Config c = config; return c == null ? -1 : c.timeout; }
    // The JMM allows read() to return 0: the reference was seen before the field write.
}

// Fixes — any one of these is enough:
static volatile Config config;           // volatile publication
// or:  final int timeout;               // final-field freeze guarantee
// or:  private static final Config CONFIG = new Config(30);  // class-init publication

// `this` escape — also unsafe, even with final fields:
Listener(EventBus bus) { bus.register(this); this.state = load(); } // bus thread may run first
```

**Pourquoi c'est un piège :** « ça marche sur ma machine » est *précisément* à quoi ressemble une publication non sûre,
car le réordonnancement dépend du matériel et du JIT. Les candidats qui disent « volatile ne sert que pour les
flags » ratent que son vrai rôle est l'arête happens-before qui rend visible le *reste* d'un objet.

#### Q17. Quand choisiriez-vous `ReentrantLock` (ou `StampedLock`) plutôt que `synchronized` ?
**Réponse :** `synchronized` est le bon choix par défaut : il relâche le monitor automatiquement même sur
une exception, ne peut pas être oublié, et la JVM l'optimise fortement. Ne recourez à
`java.util.concurrent.locks` que lorsque vous avez besoin de quelque chose qu'il ne peut pas exprimer : **`tryLock()` /
`tryLock(timeout)`** pour éviter d'attendre indéfiniment (l'outil pratique pour casser les deadlocks, S8),
**`lockInterruptibly()`** pour qu'un thread en attente puisse être annulé, une politique d'ordonnancement **fair**,
plusieurs files **`Condition`** sur un même lock (un bounded buffer avec des `notFull` et
`notEmpty` séparés), ou un locking **hand-over-hand** qui ne rentre pas dans un bloc lexical. Le prix est
la discipline : le unlock *doit* être dans un `finally`, sinon une seule exception laisse le lock détenu pour toujours.
`ReadWriteLock` et `StampedLock` ciblent les données à lecture majoritaire : `StampedLock` ajoute une **lecture
optimiste** (lire sans verrouiller, puis `validate(stamp)` ; réessayer sous un vrai read lock si un écrivain
est intervenu), ce qui peut battre un read-write lock sous forte contention en lecture — mais il n'est **pas
réentrant**, n'a pas de `Condition`s, et le ré-entrer depuis le même thread provoque un deadlock avec lui-même. Sur
JDK 21–23, `synchronized` autour d'un I/O bloquant épingle aussi un virtual thread à son carrier (Q23,
S11), ce qui est une raison d'utiliser `ReentrantLock` dans ce cas ; JDK 24 (JEP 491) a supprimé l'essentiel de ce
pinning, donc l'argument s'est affaibli sur les JDK actuels.

**Exemple :**
```java
// Deadlock-avoiding transfer: give up and retry instead of waiting forever.
boolean transfer(Account a, Account b, long amount) throws InterruptedException {
    if (a.lock.tryLock(50, TimeUnit.MILLISECONDS)) {
        try {
            if (b.lock.tryLock(50, TimeUnit.MILLISECONDS)) {
                try { a.debit(amount); b.credit(amount); return true; }
                finally { b.lock.unlock(); }
            }
        } finally { a.lock.unlock(); }
    }
    return false;                         // caller retries with backoff
}

// StampedLock optimistic read: no lock taken on the fast path.
double distance() {
    long stamp = sl.tryOptimisticRead();
    double x = this.x, y = this.y;        // copy to locals
    if (!sl.validate(stamp)) {            // a writer intervened -> fall back
        stamp = sl.readLock();
        try { x = this.x; y = this.y; } finally { sl.unlockRead(stamp); }
    }
    return Math.hypot(x, y);
}
```

**Pourquoi c'est un piège :** « `ReentrantLock` est plus rapide » est le mauvais titre — la différence de
débit est généralement négligeable sur les JVM modernes. La réponse senior porte sur les *capacités*
(timeouts, interruption, conditions) et sur la responsabilité accrue de déverrouiller correctement.

#### Q18. L'initialisation de classe peut-elle elle-même provoquer un deadlock, et comment se comporte l'échec d'un static initializer par la suite ?
**Réponse :** Oui. La JVM garantit que chaque classe est initialisée exactement une fois en détenant un
lock d'initialisation pendant l'exécution des initialiseurs `static` (JLS §12.4.2). Si l'initialiseur static de la classe `A`
a besoin de la classe `B`, et celui de `B` a besoin de `A`, et que deux threads différents déclenchent `A` et `B`
en premier presque au même moment, chacun détient le lock d'init d'une classe et attend l'autre —
un deadlock fait de *class loading*, et non d'un quelconque `synchronized` dans votre code. Il est intermittent
parce qu'il exige cet entrelacement exact, et il est facile à manquer dans un thread dump : le détecteur classique de
deadlock ne rapporte souvent rien, mais les deux stacks se trouvent dans des frames `<clinit>`. Un piège connexe
est le comportement en cas d'échec : si un static initializer lève une exception, le premier utilisateur voit
`ExceptionInInitializerError`, et **chaque utilisation ultérieure dans cette JVM** voit
`NoClassDefFoundError: Could not initialize class X` — la classe est définitivement empoisonnée jusqu'au
redémarrage, et la seconde erreur masque la cause d'origine (chercher dans les logs la *première*).
Règles qui préviennent les deux : garder les static initializers triviaux, ne jamais y démarrer de threads ni y faire d'I/O,
et casser les références statiques cycliques avec un lazy holder (Q19).

**Exemple :**
```java
class A { static final B PARTNER = new B(); static void touch() {} }
class B { static final A PARTNER = new A(); static void touch() {} }

// Thread 1: A.touch();  -> holds A's init lock, needs B initialized
// Thread 2: B.touch();  -> holds B's init lock, needs A initialized
// Both block forever inside <clinit>; no synchronized keyword appears anywhere.

// Poisoned class:
class Settings {
    static final int PORT = Integer.parseInt(System.getenv("PORT")); // env var missing
}
// 1st use: ExceptionInInitializerError (cause: NumberFormatException)
// 2nd use onward: NoClassDefFoundError: Could not initialize class Settings
```

**Pourquoi c'est un piège :** les candidats supposent que les deadlocks exigent deux locks explicites. Le second
`NoClassDefFoundError` est le faux indice habituel lors d'un incident : les ingénieurs poursuivent un « jar manquant »
qui est en réalité présent, alors que le vrai bug est la première erreur d'initialiseur, depuis longtemps sortie du scroll.

#### Q19. Nommez les stratégies d'implémentation d'un Singleton thread-safe, et expliquez pourquoi Bill Pugh / static inner class est généralement préféré.
**Réponse :** Quatre approches courantes : (1) l'initialisation eager — un champ `static final`,
instancié au chargement de la classe, simple et thread-safe mais qui paie toujours le coût de construction
même s'il n'est pas utilisé ; (2) un `getInstance()` synchronized — correct mais sérialise chaque appel pour toujours,
même après l'existence de l'instance ; (3) le double-checked locking avec un champ `volatile` — lazy et
rapide après le premier appel, mais facile à rater sans `volatile` (voir Q15) ; (4) la
holder class interne statique de Bill Pugh — une classe imbriquée statique privée détient l'instance `static final`, et
la JVM ne charge (et donc n'initialise) cette classe imbriquée que la première fois qu'elle est référencée,
ce qui donne une initialisation lazy sans aucune synchronisation, garantie par la thread-safety
du class loading de la JVM. Elle est préférée au double-checked locking parce qu'elle obtient la laziness et la thread
safety gratuitement, sans la subtilité qu'exige ce pattern. Un `enum` à valeur unique est l'
autre approche couramment citée, et elle n'est *pas* simplement équivalente à Bill Pugh : elle est aussi
thread-safe et lazy par construction, mais elle protège en plus contre deux attaques que Bill Pugh
ne couvre pas — la réflexion (un appelant peut forcer un constructeur privé à s'exécuter deux fois via
`Constructor.setAccessible(true)`, mais la JVM garantit qu'un constructeur d'enum s'exécute exactement une fois
par constante) et la désérialisation (un singleton écrit à la main qui implémente `Serializable` peut être
désérialisé en une toute nouvelle seconde instance sauf si vous ajoutez explicitement `readResolve()` ; les enums
gèrent cela correctement sans code supplémentaire). Donc le vrai classement pour une réponse senior n'est pas « Bill
Pugh et enum conviennent tous les deux » — c'est « l'enum est strictement plus robuste face à une duplication malveillante ou
accidentelle ; Bill Pugh est le bon choix principalement quand le singleton ne peut pas être un enum
(par ex. il doit étendre une autre classe). »

**Exemple :**
```java
public class Registry {
    private Registry() { /* ... */ }

    private static class Holder {
        static final Registry INSTANCE = new Registry();
    }

    public static Registry getInstance() {
        return Holder.INSTANCE; // Holder class loads lazily, on first call, no lock needed
    }
}

// Reflection can still break Registry:
Constructor<Registry> c = Registry.class.getDeclaredConstructor();
c.setAccessible(true);
Registry second = c.newInstance(); // succeeds — a second, distinct instance

// An enum singleton closes that hole:
public enum EnumRegistry {
    INSTANCE;
}
// EnumRegistry.class.getDeclaredConstructor() throws NoSuchMethodException —
// enum constructors aren't invocable via reflection this way.
```

**Pourquoi c'est un piège :** traiter Bill Pugh et `enum` comme des « meilleures » réponses interchangeables — un
recruteur qui creuse (« et la réflexion ? ») teste si vous connaissez réellement la
faille, et pas seulement le nom du pattern.

#### Q20. Pourquoi les `ThreadLocal`s conviennent-ils mal au code concurrent moderne, et que change `ScopedValue` ?
**Réponse :** Un `ThreadLocal` est un emplacement par thread, mutable et sans portée : n'importe qui peut le `set()`, il
vit jusqu'à ce que quelqu'un pense à le `remove()`, et sur un thread poolé il fait fuiter silencieusement la
valeur de la requête précédente dans la suivante (Q27). Il coûte aussi de la mémoire par thread, ce qui cesse
d'être anodin à l'échelle des virtual threads (Q23) — un million de virtual threads signifie jusqu'à un million
de copies de chaque valeur de `ThreadLocal` — et `InheritableThreadLocal` copie les valeurs dans chaque thread
enfant de façon eager. `ScopedValue` (une API preview dans JDK 21–24, finale dans JDK 25) corrige la conception
plutôt que le symptôme : la valeur est **immuable**, **liée pour une portée bornée**
(`ScopedValue.where(KEY, v).run(...)`), automatiquement disparue à la sortie de cette portée (pas de fuite, pas de
`finally { remove(); }`), et **héritée à faible coût** par les threads forkés dans la portée via la
structured concurrency, sans copie. Le coût du changement : c'est à sens unique (un appelé ne peut pas
`set` une valeur que l'appelant relit — il ne peut que la re-lier pour une portée imbriquée), donc un
*contexte* par requête (utilisateur, trace id, tenant) convient parfaitement alors que des *caches mutables* par thread non. Tant que
vous ne pouvez pas migrer, gardez l'usage de `ThreadLocal` minuscule, encapsulez-le dans une seule classe avec un `try/finally` qui
le vide toujours, et n'y stockez jamais d'objets lourds.

**Exemple :**
```java
// ThreadLocal: must be cleared manually or it leaks into the next task on a pooled thread.
static final ThreadLocal<User> CURRENT = new ThreadLocal<>();

void handle(Request r) {
    CURRENT.set(auth(r));
    try { service.process(r); }
    finally { CURRENT.remove(); }         // forget this line -> data bleeds between requests
}

// ScopedValue (JDK 25): bound for the lifetime of run(), then automatically unbound.
static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

void handle(Request r) {
    ScopedValue.where(CURRENT_USER, auth(r))
               .run(() -> service.process(r));   // service can call CURRENT_USER.get()
}
```

**Pourquoi c'est un piège :** la réponse qui sonne solide « ThreadLocal, ça va, il suffit d'appeler `remove()` »
ignore que la correction dépend alors de chaque chemin de code qui doit y penser — tout l'intérêt de la
question est de savoir si vous pouvez expliquer *pourquoi* un global mutable sans portée par thread est la mauvaise
abstraction, et pas seulement réciter la fuite.

### Executors & async

#### Q21. Quelle est la différence entre utiliser `ExecutorService` et créer des objets `Thread` bruts, et quel est un piège courant avec le common fork-join pool ?
**Réponse :** `ExecutorService` découple la soumission des tâches de la gestion des threads — vous soumettez
des `Runnable`s ou `Callable`s à un pool de taille bornée (ou un virtual-thread-per-task), récupérez des
`Future`s, et le pool gère la réutilisation, la mise en file et l'arrêt ; la création brute de `Thread` ne vous donne rien
de tout cela et ne passe pas à l'échelle au-delà d'une poignée de threads. Le piège courant : `parallelStream()` et
les méthodes async par défaut de `CompletableFuture` (`thenApplyAsync` sans executor explicite, etc.)
utilisent toutes deux le `ForkJoinPool.commonPool()` partagé, dimensionné par défaut à
`availableProcessors() - 1` — y soumettre un appel I/O bloquant (une requête JDBC, un appel HTTP)
peut affamer *tous les autres* parallel streams et `CompletableFuture` async par défaut de l'ensemble du processus
JVM, puisqu'ils partagent tous ce seul pool, y compris ceux de bibliothèques sans rapport que vous ne
contrôlez pas. Le travail bloquant appartient à son propre executor dédié, dimensionné pour la charge bloquante
(souvent bien plus grand que le nombre de CPU, puisque les threads bloqués ne consomment pas de CPU).

**Exemple :**
```java
// Dangerous: a slow HTTP call inside parallelStream() eats a commonPool thread
// that every other parallelStream() call in the JVM is also competing for.
List<String> results = urls.parallelStream()
    .map(url -> httpClient.get(url)) // blocking call on the shared commonPool
    .toList();

// Fix: give blocking work its own dedicated, sized-for-blocking pool.
ExecutorService ioPool = Executors.newFixedThreadPool(50);
List<Future<String>> futures = urls.stream()
    .map(url -> ioPool.submit(() -> httpClient.get(url)))
    .toList();
```

**Pourquoi c'est un piège :** le bug n'apparaît pas dans le code qui le contient — il apparaît sous la forme d'un
ralentissement sans rapport apparent, apparemment aléatoire, dans une partie complètement différente de l'application qui
utilise elle aussi `parallelStream()` ou des `CompletableFuture` async par défaut.

#### Q22. Décrivez `thenApply` vs `thenCompose` vs `thenCombine` sur `CompletableFuture`, et nommez un piège courant.
**Réponse :** `thenApply` transforme le résultat avec une fonction simple (`T -> U`) — à utiliser quand
l'étape suivante n'est pas elle-même async. `thenCompose` aplatit une étape qui *retourne* un autre
`CompletableFuture` (`T -> CompletableFuture<U>`) — l'équivalent async de `flatMap` ; utiliser
`thenApply` ici vous donnerait un `CompletableFuture<CompletableFuture<U>>`, ce qui signifie presque toujours
que celui qui le consomme a oublié de déballer une couche. `thenCombine` joint deux futures *indépendants*
une fois les deux terminés, en exécutant une `BiFunction` sur les deux résultats. Le piège courant est d'appeler
`.get()` ou `.join()` sur un future à l'intérieur du callback d'un autre future (ou pire, sur un thread
de requête) — cela bloque un thread en attente d'un travail async, ce qui va à l'encontre de l'objectif et, sur le
common pool, risque la même famine qu'à la Q21. Composez la chaîne au lieu de bloquer en cours de route.

**Exemple :**
```java
CompletableFuture<User> userFuture = fetchUser(id);

// Wrong shape: thenApply on a step that returns a future -> nested future.
CompletableFuture<CompletableFuture<Order>> nested =
    userFuture.thenApply(user -> fetchLatestOrder(user)); // fetchLatestOrder returns a CF<Order>

// Correct: thenCompose flattens it.
CompletableFuture<Order> flat =
    userFuture.thenCompose(user -> fetchLatestOrder(user));

// Combining two independent futures:
CompletableFuture<Profile> profileFuture = fetchProfile(id);
CompletableFuture<Dashboard> dashboard =
    flat.thenCombine(profileFuture, (order, profile) -> new Dashboard(order, profile));
```

**Pourquoi c'est un piège :** le compilateur accepte sans problème la version `thenApply` avec un future imbriqué —
c'est un bug de forme de type, pas une erreur de syntaxe, donc il n'apparaît que lorsqu'un appelant essaie d'utiliser le
résultat et obtient un `CompletableFuture` là où il attendait la vraie valeur.

#### Q23. Quel problème les virtual threads (Project Loom) résolvent-ils réellement, et où échouent-ils encore ?
**Réponse :** Les platform threads sont de fines enveloppes autour de threads OS — coûteux à créer
(stacks de l'ordre du mégaoctet) et limités en nombre (des milliers, pas des millions), ce qui explique pourquoi
les serveurs I/O-bound à forte concurrence se sont historiquement tournés vers la programmation réactive/async
(callbacks, chaînes de `CompletableFuture`, WebFlux) pour éviter de bloquer un thread rare sur un appel
réseau lent. Les virtual threads sont gérés par la JVM, bon marché (kilooctets, des millions possibles), et quand un
virtual thread bloque sur de l'I/O, la JVM le démonte de son platform thread carrier et libère ce
platform thread pour exécuter d'autres virtual threads — on peut donc écrire du code ordinaire bloquant et séquentiel
(`InputStream.read()`, appels JDBC) et obtenir quand même une scalabilité de type réactif en coulisses,
sans restructurer le code en callbacks. Les deux endroits où cela pose encore problème en production : (1)
un virtual thread qui bloque *à l'intérieur* d'un bloc `synchronized` ne peut pas être démonté — il épingle
son carrier thread à la place, reproduisant silencieusement l'ancien problème de famine de threads (voir S11) ; et (2)
comme les virtual threads sont si bon marché que les gens en lancent des millions, tout état par thread
qui était « gratuit » à l'échelle des platform threads — le plus souvent un `ThreadLocal` contenant un gros
objet — cesse de l'être, puisqu'il est maintenant multiplié par des ordres de grandeur de threads en plus, et
`ThreadLocal` n'a jamais été conçu avec cette cardinalité en tête.

**Exemple :**
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 100_000; i++) {
        executor.submit(() -> {
            // Ordinary blocking JDBC/HTTP call here — the JVM unmounts this
            // virtual thread from its carrier while it waits, instead of
            // parking a whole OS thread.
            Thread.sleep(Duration.ofMillis(50));
        });
    }
} // platform threads would never scale to 100,000 concurrent blocking tasks like this
```

**Pourquoi c'est un piège :** « les virtual threads rendent le code bloquant gratuit » n'est vrai que jusqu'à ce qu'un
bloc `synchronized` ou un `ThreadLocal` surdimensionné soit sur le hot path — un recruteur qui demande
« qu'est-ce qui pourrait mal tourner ? » vérifie si vous connaissez les deux modes de défaillance concrets, pas seulement le
bénéfice affiché.

#### Q24. Quand choisiriez-vous des virtual threads plutôt qu'une stack réactive (WebFlux) pour un service I/O-bound à forte concurrence, et inversement ?
**Réponse :** Les virtual threads (Q23) l'emportent quand le codebase, ses bibliothèques et son outillage de debug
supposent du code bloquant et synchrone — la plupart des drivers JDBC, la plupart de la logique métier existante, des stack traces
qui se lisent de haut en bas — et que vous voulez une concurrence à l'échelle réactive sans réécriture réactive
complète ; vous obtenez cette scalabilité essentiellement « gratuitement » sur du code bloquant non modifié, et les thread
dumps restent lisibles. Reactive/WebFlux l'emporte encore quand vous avez besoin d'une vraie sémantique de backpressure (un
consommateur lent signalant explicitement à un producteur rapide de ralentir — les virtual threads ne vous donnent pas
cela, puisque chaque virtual thread exécute toujours le code synchrone que vous avez écrit, sans signal au
producteur pour ralentir), ou quand vos sources de données sont déjà entièrement non bloquantes de bout en bout
(R2DBC, Mongo réactif) et les réécrire en bloquant reviendrait à jeter cet acquis. En pratique : par défaut,
préférer les virtual threads pour les services CRUD/proxy/orchestration typiques maintenant qu'ils sont stables et que les
bibliothèques bloquantes « fonctionnent simplement » dessus ; recourir au réactif spécifiquement quand la backpressure ou un
pipeline entièrement non bloquant est l'exigence réelle, pas un choix par défaut fait parce que
« le réactif, c'est la manière moderne ».

**Exemple :**
```java
// Virtual-thread style: ordinary blocking code, scales via cheap threads.
@GetMapping("/orders/{id}")
String getOrder(@PathVariable String id) {
    return jdbcTemplate.queryForObject(
        "select * from orders where id = ?", String.class, id); // blocks the virtual thread only
}

// Reactive style: explicit backpressure-aware pipeline, no thread blocks at all.
@GetMapping("/orders/{id}")
Mono<String> getOrderReactive(@PathVariable String id) {
    return r2dbcTemplate.selectOne(Query.query(where("id").is(id)), String.class);
}
```

**Pourquoi c'est un piège :** « utilisez des virtual threads partout, le réactif est obsolète maintenant » est une
surcorrection — c'est vrai pour le cas CRUD courant mais faux dès que la backpressure ou un aval
déjà réactif est une exigence réelle, et une réponse senior nomme cette frontière
au lieu de choisir un vainqueur universel.

### Mémoire JVM & GC

#### Q25. Expliquez l'analyse d'accessibilité (reachability) et les GC roots, et nommez deux algorithmes de garbage collection.
**Réponse :** La JVM n'utilise pas de comptage de références ; elle trace périodiquement l'accessibilité depuis un
ensemble fixe de **GC roots** — variables locales et paramètres sur la stack de chaque thread vivant,
champs statiques, références JNI détenues par du code natif, et quelques autres (monitors actifs, références
internes de la JVM) — en suivant chaque référence transitivement. Tout ce qui n'est pas accessible depuis une
root est du garbage, quel que soit le nombre d'objets qui se référencent mutuellement (c'est pourquoi les
cycles de références ne sont pas une fuite en Java, contrairement au comptage de références naïf — deux objets qui ne se référencent que
entre eux mais que rien d'autre n'atteint sont quand même collectés ensemble). Deux algorithmes nommés :
**G1 (Garbage First)**, le défaut depuis Java 9, qui divise le heap en régions de taille fixe
et collecte en premier celles qui contiennent le plus de garbage, visant un objectif de temps de pause configurable
plutôt qu'une disposition fixe en générations ; et **ZGC**, un collector concurrent à faible latence
(pauses cibles inférieures à la milliseconde même sur de très grands heaps, utilisant des colored pointers et des load barriers
pour faire le marquage et la relocalisation en concurrence avec les threads applicatifs) dont le temps de pause reste
à peu près plat quelle que soit la taille du heap, contrairement aux pauses de G1 qui croissent encore quelque peu avec la taille
du live set.

**Exemple :**
```java
class Node {
    Node other;
}

void demo() {
    Node a = new Node();
    Node b = new Node();
    a.other = b;
    b.other = a; // a and b reference each other — a reference-counting GC would leak this

    a = null;
    b = null;
    // Neither local variable is a GC root anymore, so the a<->b cycle
    // is unreachable as a whole and gets collected on the next cycle,
    // despite the objects still referencing each other.
}
```

**Pourquoi c'est un piège :** les candidats issus d'un langage à comptage de références (Python, Swift,
Objective-C) supposent parfois que Java a le même problème de fuite par cycle que ces langages ont sans
collector de cycles — le GC tracing de Java n'a jamais eu ce problème.

#### Q26. Décrivez comment choisir entre G1, ZGC et Shenandoah pour un service sensible à la latence.
**Réponse :** Partez de la contrainte réelle, pas du nom du collector : G1 est le défaut sûr —
mature, bien compris, basé sur des régions, avec des objectifs de temps de pause ajustables (`-XX:MaxGCPauseMillis`) — et
convient à la plupart des services où « une pause occasionnelle de quelques dizaines de millisecondes » est acceptable. Si le
service a un budget de pause strict inférieur à 10 ms (ou à la milliseconde) quelle que soit la taille du heap — un système
de trading, un chemin de real-time bidding — ZGC et Shenandoah sont les collectors concurrents à faible pause,
qui font le marquage et le compactage en concurrence avec les threads applicatifs au lieu de stopper le monde
pour cela ; ZGC en particulier fait évoluer le temps de pause indépendamment de la taille du heap (via colored pointers
et load barriers, voir Q25), donc il reste plat même sur de très grands heaps (des centaines de Go), alors que
les pauses stop-the-world de G1 augmentent encore quelque peu avec un live set plus grand. Le compromis pour les deux
collectors concurrents est un overhead CPU un peu plus élevé (le travail concurrent entre en compétition avec les threads
applicatifs pour les cœurs) et, historiquement, un coût en débit par rapport à G1 — même si cet écart s'est réduit
de façon significative dans les versions récentes du JDK. La réponse digne d'un entretien énonce d'abord l'exigence réelle de
latence (un nombre, en millisecondes, lié à un SLO), puis choisit le collector qui y correspond,
plutôt que de partir par défaut sur « ZGC est plus récent donc meilleur » — un job ETL batch sans exigence de
latence côté utilisateur ne tire rien des faibles pauses de ZGC et paie son overhead CPU sans aucun bénéfice.

**Exemple :**
```
# G1 — safe default, tunable pause goal:
-XX:+UseG1GC -XX:MaxGCPauseMillis=200

# ZGC — sub-millisecond pauses, flat regardless of heap size, more CPU overhead:
-XX:+UseZGC

# Choosing between them isn't a flag decision, it's an SLO decision:
# "p99 request latency must stay under 15ms" -> ZGC is a candidate.
# "occasional 100ms pause is acceptable, we care more about throughput" -> G1.
```

**Pourquoi c'est un piège :** choisir un collector sur sa réputation (« ZGC est le plus rapide ») plutôt que sur le
SLO de latence réel du service est un signal d'alarme — un job batch sans exigence de latence ne gagne
rien avec ZGC et en paie l'overhead pour rien, alors qu'un service avec un budget réel inférieur à 10 ms
qui reste sur G1 « parce que c'est le défaut » ne satisfait pas sa propre exigence.

#### Q27. Java a un garbage collection — comment une fuite mémoire peut-elle encore se produire ?
**Réponse :** Le GC ne récupère que les objets *inaccessibles* ; une « fuite » en Java est en réalité une accessibilité
involontaire — quelque chose détient encore une référence vers des objets dont plus personne n'a besoin, donc ils ne
deviennent jamais éligibles à la collecte. Causes classiques : une collection `static` (cache, liste de listeners) qui
ne fait que grossir et n'est jamais élaguée ; des listeners/callbacks enregistrés jamais désenregistrés, maintenant en vie
tout le graphe d'objets qu'ils capturent ; et des valeurs de `ThreadLocal` non vidées avant qu'un thread ne soit
rendu à un pool — comme les threads poolés vivent indéfiniment, tout ce qui reste dans leur map `ThreadLocal`
vit avec eux, ce qui est une fuite particulièrement vicieuse dans les thread pools d'app-server car elle est
invisible jusqu'à ce que le heap grossisse depuis des jours. Les virtual threads (Q23) ne suppriment pas ce risque ;
ils peuvent l'aggraver en volume, car un mauvais usage de `ThreadLocal` qui était borné par « quelques centaines de
platform threads dans le pool » devient non borné par « autant de virtual threads qui se trouvent être vivants
en ce moment » si la valeur n'est jamais vidée.

**Exemple :**
```java
class RequestContext {
    private static final ThreadLocal<byte[]> BUFFER = ThreadLocal.withInitial(() -> new byte[1_000_000]);

    void handle() {
        BUFFER.get(); // do work with a per-thread scratch buffer
        // missing: BUFFER.remove();
        // On a pooled platform thread, this 1 MB buffer lives forever, tied to
        // that thread — multiply by pool size and it's a slow, steady leak.
    }
}
```

**Pourquoi c'est un piège :** « le GC gère la mémoire pour moi » est l'hypothèse qui est remise en cause ici —
le recruteur veut entendre qu'une fuite est un bug d'accessibilité dont l'*application* est responsable, et non
quelque chose qu'on pourrait attendre d'un garbage collector qu'il détecte ou corrige.

#### Q28. Quelle est la différence entre `StackOverflowError` et `OutOfMemoryError`, et d'où vient réellement chacune ?
**Réponse :** Les deux sont des `Error`s (pas des `Exception`s — la JVM signale quelque chose dont l'application
ne devrait généralement pas essayer de se remettre), mais elles viennent de régions mémoire différentes.
`StackOverflowError` se produit quand la call stack d'un seul thread dépasse sa taille fixe — presque
toujours une récursion non bornée ou excessivement profonde ; augmenter `-Xss` la retarde mais un vrai bug de
récursion infinie l'atteindra quand même tôt ou tard, simplement plus tard. `OutOfMemoryError` se produit sur
le heap (`OutOfMemoryError: Java heap space`, quand les objets vivants plus le garbage dépassent le
heap configuré et que le GC ne peut pas en libérer assez), ou dans le metaspace (`OutOfMemoryError: Metaspace`, dû au
chargement de trop de classes — un symptôme classique de fuite de classloader, voir S12), ou même à cause de trop de
threads (`OutOfMemoryError: unable to create new native thread`, atteignant une limite de threads OS,
ce qui est une raison de plus pour laquelle les virtual threads (Q23) ont changé le mode de défaillance du code à forte concurrence —
cette erreur précise devient bien moins probable quand les threads sont bon marché) — le message spécifique après
les deux-points est la première chose à lire, puisque la correction diffère complètement selon la région.

**Exemple :**
```java
// StackOverflowError — unbounded recursion, not a heap problem at all.
long factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1); // no base-case bug needed —
                                               // a large enough n alone overflows the stack
}

// OutOfMemoryError: Java heap space — a genuinely unbounded live set.
List<byte[]> leak = new ArrayList<>();
while (true) {
    leak.add(new byte[1_000_000]); // never removed, always reachable via `leak`
}
```

**Pourquoi c'est un piège :** les candidats recourent parfois à « augmenter le heap » ou « augmenter la taille de
la stack » comme correction universelle pour les deux — cela traite le symptôme, pas la cause racine propre à chaque région,
et les deux erreurs continuent de se reproduire (simplement plus tard) si l'algorithme sous-jacent est réellement non borné.

## 🎯 Scénarios réels

### S1. Un service de production lève `OutOfMemoryError: Java heap space` après un pic de trafic
- **Symptômes :** Le service était sain pendant des semaines, puis lors d'un pic de trafic lié à une campagne marketing
  il se met à lever `OutOfMemoryError: Java heap space` et est OOMKilled ou redémarré par
  l'orchestrateur.
- **Diagnostic :** Récupérer un heap dump à la prochaine occurrence (`-XX:+HeapDumpOnOutOfMemoryError` devrait
  déjà être positionné en prod) et le charger dans un analyseur mémoire pour trouver le dominator tree — ce qui
  retient le plus de mémoire. Recouper avec le monitoring : cette taille de heap était-elle toujours limite et
  le pic l'a-t-il simplement exposée (augmenter le heap ou ajouter des replicas), ou la mémoire retenue a-t-elle crû
  sans borne avec le volume de requêtes (une vraie fuite, probablement un cache ou une collection non bornée liée
  au nombre de requêtes) ?
- **Exemple :**
  ```java
  // A classic accidental leak: caching per-request data in a static map that's
  // sized fine at low traffic but scales unboundedly with the traffic spike.
  static final Map<String, Response> responseCache = new HashMap<>(); // never evicted

  Response handle(Request req) {
      return responseCache.computeIfAbsent(req.key(), k -> compute(req));
  }
  ```
- **Résolution :** Si le heap est réellement sous-dimensionné, augmenter `-Xmx` et/ou ajouter de la capacité horizontale. Si
  c'est une fuite, corriger la référence qui retient (ajouter de l'éviction/une borne à la
  collection/au cache fautif, par ex. le remplacer par un cache Caffeine borné) et redéployer ; vérifier que le heap
  atteint maintenant un plateau sous charge soutenue au lieu de grimper.
- **Prévention :** Faire des tests de charge avec un trafic représentatif de la production avant les événements très visibles,
  alerter sur la tendance d'usage du heap (pas seulement sur un seuil — une montée régulière est la signature de la fuite), et
  utiliser par défaut pour les nouveaux caches une implémentation bornée (Caffeine avec une taille max) plutôt qu'une simple
  `HashMap`.

### S2. L'application se fige plusieurs secondes d'affilée, apparemment au hasard
- **Symptômes :** Pas d'erreurs, pas de crashs, mais les graphes de latence montrent des pics périodiques où chaque
  requête se bloque pendant 2 à 5 secondes simultanément, puis récupère.
- **Diagnostic :** Ce schéma — tout se met en pause en même temps — est la signature d'une pause GC
  stop-the-world, pas de la logique applicative. Activer/consulter les logs GC (`-Xlog:gc*`) et corréler les
  horodatages des pauses avec les pics de latence ; s'ils coïncident, c'est confirmé.
- **Exemple :**
  ```
  [12.481s][info][gc] GC(42) Pause Full (Allocation Failure) 1998M->1950M(2048M) 2412.331ms
  ```
  Une ligne `Pause Full` de plus de 2 secondes coïncidant exactement avec un pic de latence de requête au même
  horodatage est la preuve qui confirme — pas une coïncidence à balayer.
- **Résolution :** Selon ce que montre le log GC : si les pauses sont corrélées à des full GCs, la
  young generation est peut-être sous-dimensionnée (trop d'objets promus trop tôt) — ajuster le
  dimensionnement des générations avant de changer de collector. Si les pauses sont fréquentes mais que l'objectif de temps de pause
  lui-même est trop lâche, resserrer `-XX:MaxGCPauseMillis`. Si le service a un budget de latence réellement strict
  que le collector actuel ne peut atteindre même ajusté, c'est le cas pour passer à ZGC/Shenandoah (Q26).
- **Prévention :** Envoyer les métriques de pauses GC sur le même dashboard que la latence des requêtes pour que cette
  corrélation soit une vérification de cinq secondes la prochaine fois, et non une nouvelle investigation ; définir un SLO de temps de
  pause GC à côté du SLO de latence des requêtes.

### S3. `ConcurrentModificationException` apparaît par intermittence dans les logs de production
- **Symptômes :** Un job en arrière-plan ou un handler de requête lève occasionnellement
  `ConcurrentModificationException`, mais ce n'est pas reproductible en local et cela n'arrive pas à
  chaque exécution.
- **Diagnostic :** Trouver chaque endroit où la collection de la stack trace est itérée et chaque endroit où
  elle est modifiée structurellement ; intermittent signifie que cela n'échoue que lorsqu'une modification tombe
  par hasard pendant une itération active ailleurs — souvent un champ partagé itéré dans un thread pendant qu'un
  autre thread (une tâche planifiée, un event listener) y ajoute/retire concurremment.
- **Exemple :**
  ```java
  class SubscriptionRegistry {
      private final List<Listener> listeners = new ArrayList<>();

      void notifyAll(Event e) {
          for (Listener l : listeners) l.onEvent(e); // thread A iterating
      }

      void unregister(Listener l) {
          listeners.remove(l); // thread B mutating concurrently — CME if they overlap
      }
  }
  ```
- **Résolution :** Si c'est une logique réellement mono-thread avec un mauvais schéma de remove-pendant-l'itération,
  passer à `Iterator.remove()` ou `removeIf` (Q13). Si c'est un accès inter-threads à un état mutable partagé,
  c'est le vrai bug — soit rendre l'accès mono-thread (en passant par un seul
  executor), soit passer à une collection concurrente adaptée au schéma d'accès
  (`ConcurrentHashMap`, `CopyOnWriteArrayList` pour lecture majoritaire/écriture rare, ce qui convient bien à une liste de
  listeners puisque l'enregistrement est rare et la notification fréquente).
- **Prévention :** Traiter toute collection mutable accessible depuis plus d'un thread comme un
  point d'attention en code review ; documenter la propriété (quel thread/composant a le droit de la muter) directement
  dans la déclaration du champ.

### S4. Une recherche basée sur `HashMap` qui était rapide est devenue de plus en plus lente au fil des mois
- **Symptômes :** Un cache ou un index indexé par un type d'objet personnalisé était rapide au lancement ; les temps de réponse
  de cette recherche ont dérivé à mesure que le jeu de données grossissait, de façon disproportionnée par rapport à la croissance du nombre
  d'entrées.
- **Diagnostic :** Vérifier l'implémentation de `hashCode()` du type de clé (Q11). Un bug courant :
  `hashCode()` n'a jamais été redéfini (retombe sur le hash d'identité de `Object`, qui convient pour la
  distribution mais casse l'égalité logique entre instances construites séparément) *ou* a été
  redéfini incorrectement — par ex. basé sur un champ constant ou de faible cardinalité pour la plupart des
  entrées, ce qui regroupe la plupart des clés dans une poignée de buckets.
- **Exemple :**
  ```java
  class OrderKey {
      final String region; // only 4 possible values across millions of orders
      final String orderId;

      @Override public int hashCode() { return region.hashCode(); } // ignores orderId — bad!
      @Override public boolean equals(Object o) {
          return o instanceof OrderKey k && region.equals(k.region) && orderId.equals(k.orderId);
      }
  }
  // Every key in the same region collapses into the same bucket — O(n) lookups.
  ```
- **Résolution :** Corriger `hashCode()` pour qu'il incorpore tous les champs utilisés dans `equals()` avec une bonne
  distribution (`Objects.hash(region, orderId)` est le défaut sûr), et s'assurer que `equals()`
  et `hashCode()` restent cohérents (des objets égaux doivent avoir des hashes égaux). Vérifier en contrôlant la
  distribution des buckets avant/après, ou simplement en re-mesurant la latence de recherche au même volume
  de données.
- **Prévention :** Générer `equals()`/`hashCode()` avec l'IDE ou `record`/Lombok plutôt que de les
  écrire à la main, et ajouter un test qui vérifie une distribution de hash raisonnable pour tout type de clé
  personnalisé utilisé dans une map sur un hot path.

### S5. L'usage du heap grimpe régulièrement et ne redescend jamais, même sous faible charge
- **Symptômes :** L'usage du heap après chaque cycle GC tend à monter sur plusieurs jours, sans lien avec le trafic
  actuel — un classique motif en dents de scie qui ne se réinitialise jamais sur le graphe mémoire.
- **Diagnostic :** C'est une fuite, pas un problème de dimensionnement (le scénario de pic de S1 récupère entre les GCs ;
  celui-ci non). Heap dump plus analyse du dominator tree pour trouver ce qui grossit ; le coupable le plus courant
  est une `Map`/`List` `static` utilisée comme cache ad hoc avec des entrées ajoutées à chaque requête et
  jamais retirées — vérifier d'abord tout ce qui est `static`.
- **Exemple :**
  ```java
  static final Map<String, Session> activeSessions = new HashMap<>();

  void onLogin(String userId, Session session) {
      activeSessions.put(userId, session); // added on login...
      // ...but the logout handler was never wired up to remove it, so every
      // session that ever logged in stays reachable via this static map.
  }
  ```
- **Résolution :** Ajouter une borne/de l'éviction à la collection fautive (plafond de taille, TTL, ou passage à
  une vraie bibliothèque de cache), ou corriger la logique sous-jacente si les entrées auraient dû être retirées sur
  un événement de cycle de vie qui ne se déclenche pas (par ex. un listener jamais désenregistré — voir Q27).
- **Prévention :** Interdire par défaut en code review les collections mutables `static` non bornées ; exiger que
  tout cache en mémoire intentionnel énonce explicitement sa borne et sa politique d'éviction.

### S6. Le CPU reste collé près de 100 % sans augmentation proportionnelle du volume de requêtes
- **Symptômes :** L'utilisation CPU monte et reste haute alors que le débit de requêtes reste plat ou
  baisse ; le service répond toujours techniquement, mais lentement.
- **Diagnostic :** Prendre un thread dump (ou plusieurs, à quelques secondes d'intervalle) et chercher des threads
  `RUNNABLE` dans la même méthode chaude d'un échantillon à l'autre — c'est une attente active ou une boucle de retry serrée, pas
  de l'attente I/O (qui apparaîtrait `WAITING`/`TIMED_WAITING`). Une cause courante : une boucle de retry sans
  backoff qui tourne contre une dépendance en échec, ou une boucle de polling avec un intervalle trop court.
- **Exemple :**
  ```java
  while (true) {
      try {
          return call(dependency);
      } catch (Exception e) {
          // no backoff, no attempt cap — a failing dependency turns this into
          // a tight CPU-burning loop, retried thousands of times per second
      }
  }
  ```
- **Résolution :** Ajouter un backoff exponentiel (avec jitter) à la boucle de retry/polling, et plafonner les
  tentatives de retry ; s'il s'agit d'une vraie boucle chaude algorithmique, la profiler (async-profiler / JFR) pour trouver
  l'inefficacité réelle plutôt que de deviner.
- **Prévention :** Ne jamais livrer une boucle de retry sans backoff ni limite de tentatives maximale ; ajouter une
  étape de runbook de thread dump sur CPU élevé pour que ce diagnostic soit routinier, et non un exercice d'urgence.

### S7. Sous charge, les requêtes commencent à expirer alors que les dépendances aval sont saines
- **Symptômes :** La latence et le taux d'erreurs grimpent fortement au-delà d'un certain seuil de requêtes concurrentes,
  alors que la base de données/les services aval affichent des temps de réponse normaux sur leurs propres
  dashboards.
- **Diagnostic :** Thread dump pendant le ralentissement ; chercher de nombreux threads `WAITING` sur la file de l'executor
  plutôt qu'en exécution active — c'est de l'épuisement de thread pool, des requêtes qui font la queue derrière un
  pool de taille fixe plutôt qu'un aval lent. Comparer la taille configurée du pool à la
  demande concurrente réelle, et vérifier si un handler fait du travail bloquant sur un pool dimensionné
  pour autre chose (le piège du common pool de la Q21, ou le pool de traitement des requêtes d'un serveur web utilisé
  pour un appel bloquant lent).
- **Exemple :**
  ```java
  @Async // uses a small default executor sized for lightweight tasks
  CompletableFuture<Report> generateReport() {
      return CompletableFuture.completedFuture(slowJdbcQuery()); // blocks that small pool's thread
  }
  ```
- **Résolution :** Dimensionner le pool selon le besoin réel de concurrence (avec une file et une politique de
  rejet, pas non bornée), ou déplacer le travail bloquant hors du pool de traitement des requêtes vers un pool dédié
  dimensionné pour cela, ou passer aux virtual threads là où la « taille du pool » cesse d'être la contrainte pour
  le travail I/O-bound (Q23).
- **Prévention :** Exposer la profondeur de la file de l'executor et le nombre de threads actifs comme métriques, pas seulement la
  latence des requêtes — une profondeur de file qui grimpe alors que la latence aval est plate est le signal spécifique
  de ce mode de défaillance, et il est invisible sans cette métrique.

### S8. Deux services (ou deux chemins de code) se bloquent occasionnellement en deadlock et cessent de progresser
- **Symptômes :** Un sous-ensemble de requêtes se bloque simplement pour toujours — pas d'erreur, aucun timeout ne se déclenche, pas de
  crash — jusqu'au redémarrage du processus.
- **Diagnostic :** Prendre un thread dump ; la JVM détecte et rapporte explicitement les deadlocks dans la sortie de
  `jstack` (« Found one Java-level deadlock »), en nommant les deux threads et les locks que chacun
  détient en attendant l'autre.
- **Exemple :**
  ```java
  // Thread A:                          // Thread B:
  synchronized (accountA) {             synchronized (accountB) {
      synchronized (accountB) { ... }       synchronized (accountA) { ... } // opposite order -> deadlock
  }                                      }
  ```
- **Résolution :** L'atténuation immédiate est de redémarrer l'instance bloquée (avec de l'alerting pour que ce ne soit
  pas silencieux). La vraie correction est d'établir un ordre d'acquisition des locks cohérent partout
  (toujours acquérir le lock A avant le lock B, jamais l'inverse dans aucun chemin de code — par ex. toujours verrouiller
  les comptes dans un ordre fixe comme par id de compte), ou de remplacer plusieurs locks par un seul lock plus grossier,
  ou d'utiliser `tryLock()` avec un timeout pour qu'un deadlock devienne un timeout récupérable au lieu de
  blocage permanent.
- **Prévention :** Garder l'ordre des locks documenté et imposé par convention (ou par une règle d'analyse
  statique) ; préférer des utilitaires de concurrence de plus haut niveau (classes `java.util.concurrent`,
  `synchronized` sur un unique objet bien défini) aux schémas multi-locks faits main.

### S9. Une comparaison de deux montants est correcte en test mais silencieusement fausse en production
- **Symptômes :** Une comparaison entre deux valeurs `Integer` se comporte correctement en test (petites
  valeurs) mais se comporte mal par intermittence en production avec des nombres réels (plus grands) — une logique qui
  devrait être équivalente à une comparaison numérique prend silencieusement la mauvaise branche.
- **Diagnostic :** Faire un grep du chemin de code pour `==` entre types boxés (`Integer`, `Long`) ; c'est le
  piège du cache d'autoboxing de la Q2 — les valeurs dans `[-128, 127]` sont par hasard `==`-égales par
  spécification, celles hors de cette plage ne le sont pas, et des données de test qui restent commodément dans cette
  plage (petits prix unitaires, petites quantités) expliquent exactement pourquoi cela a passé la review et les tests.
- **Exemple :**
  ```java
  class Invoice {
      Integer amountDue; // boxed — comes from a DB row mapper as an Integer
  }

  boolean isFullyPaid(Invoice invoice, Integer amountPaid) {
      return invoice.amountDue == amountPaid; // "works" in tests with small amounts like 50
                                               // silently wrong once a real invoice hits 200+
  }
  ```
- **Résolution :** Remplacer `==` par `.equals()` pour les comparaisons de types boxés, ou unboxer en primitif
  `int`/`long` et comparer directement ceux-ci ; ajouter un test de non-régression utilisant spécifiquement une valeur hors de la plage
  du cache (par ex. un montant de facture de 500, pas 50).
- **Prévention :** Activer une règle d'analyse statique (Error Prone, SonarQube) qui signale `==` entre
  types boxés — cette classe de bug est assez courante pour valoir la peine d'être interdite mécaniquement plutôt que
  de compter sur la review.

### S10. Une fonctionnalité fraîchement déployée plante avec `StackOverflowError` pour un sous-ensemble d'utilisateurs
- **Symptômes :** Des erreurs n'apparaissent que pour certaines entrées (par ex. fils de commentaires profondément imbriqués, grands
  arbres de catégories) juste après la livraison d'une fonctionnalité qui traite un arbre ou un graphe récursivement.
- **Diagnostic :** La stack trace elle-même est l'outil de diagnostic — elle montre les mêmes quelques frames
  répétées des centaines de fois, identifiant exactement quel appel récursif est non borné ; corréler
  les entrées en échec avec un imbriquement anormalement profond.
- **Exemple :**
  ```java
  int countDescendants(Comment comment) {
      int total = comment.replies().size();
      for (Comment reply : comment.replies()) {
          total += countDescendants(reply); // no depth guard — a 50,000-deep reply
      }                                     // chain from one abusive thread overflows the stack
      return total;
  }
  ```
- **Résolution :** Ajouter une limite de profondeur explicite avec une erreur claire avant que la propre limite de stack de la JVM
  ne soit atteinte (un `400 Bad Request` contrôlé vaut mieux qu'un crash incontrôlé), ou convertir la
  récursion en approche itérative avec une structure de données explicite pile/file si une profondeur
  arbitraire doit être supportée.
- **Prévention :** Tout algorithme récursif sur des données influencées par l'utilisateur (arbres de commentaires, hiérarchies
  de catégories, parsing JSON) a besoin d'une borne de profondeur explicite et testée dès la conception
  initiale, pas comme une réflexion après coup une fois que ça plante.

### S11. Après la migration d'un service vers les virtual threads, le débit de type thread-pool se dégrade en réalité sous charge
- **Symptômes :** Après la migration vers les virtual threads, le service dont on attendait une meilleure scalabilité
  montre au contraire de la contention sur les carrier threads — le débit plafonne bien en dessous des attentes, et
  les thread dumps montrent de nombreux virtual threads bloqués plutôt qu'en progression.
- **Diagnostic :** Chercher des blocs ou méthodes `synchronized` sur le hot path (Q23). Tant que le pinning
  n'avait pas été substantiellement amélioré dans les JDK récents, un virtual thread bloquant *à l'intérieur* d'un bloc `synchronized`
  ne peut pas être démonté de son platform thread carrier — il épingle le carrier, donc un appel
  I/O bloquant dans `synchronized` bloque ce carrier thread exactement comme l'ancien modèle, ce qui annule
  l'intérêt. Les événements de pinning de virtual threads de JFR (`jdk.VirtualThreadPinned`) le confirmeront.
- **Exemple :**
  ```java
  synchronized void processOrder(Order order) {
      paymentClient.charge(order); // blocking network call while holding the monitor
      // this virtual thread pins its carrier platform thread for the whole
      // duration of the network call — no unmounting happens inside synchronized
  }
  ```
- **Résolution :** Remplacer `synchronized` par `java.util.concurrent.locks.ReentrantLock` autour de
  toute section qui fait aussi de l'I/O bloquant — `ReentrantLock` n'épingle pas le carrier thread de la
  même façon. Ne garder `synchronized` que pour des sections critiques courtes et non bloquantes.
  ```java
  private final ReentrantLock lock = new ReentrantLock();

  void processOrder(Order order) {
      lock.lock();
      try {
          paymentClient.charge(order); // no pinning — the carrier is free while this blocks
      } finally {
          lock.unlock();
      }
  }
  ```
- **Prévention :** Lors de l'adoption des virtual threads, auditer l'usage de `synchronized` sur tout chemin qui
  effectue aussi de l'I/O dans le cadre de la migration, et non après l'apparition d'une régression.

### S12. L'usage du metaspace grossit à chaque redéploiement de l'application sur un app server de longue durée
- **Symptômes :** `OutOfMemoryError: Metaspace` après plusieurs redéploiements sur la même instance JVM
  (une configuration d'app server à hot-redeploy), alors que le code applicatif lui-même n'a pas
  visiblement grossi.
- **Diagnostic :** C'est une fuite de classloader — chaque redéploiement devrait laisser le classloader de l'ancienne application
  (et chaque classe qu'il a chargée) devenir du garbage une fois la nouvelle version en ligne, mais
  quelque chose détient encore une référence vers l'ancien classloader, donc aucune de ses classes n'est jamais
  déchargée et le metaspace accumule une copie complète des métadonnées de classes par redéploiement. Suspects
  habituels : un driver JDBC enregistré via `DriverManager` et jamais désenregistré, un `ThreadLocal`
  contenant une instance d'une classe applicative sur un thread de pool de longue durée (Q27), ou une
  référence statique dans une bibliothèque qui survit au redéploiement.
- **Exemple :**
  ```java
  // In a servlet context listener, on application shutdown:
  Enumeration<Driver> drivers = DriverManager.getDrivers();
  while (drivers.hasMoreElements()) {
      Driver d = drivers.nextElement();
      if (d.getClass().getClassLoader() == this.getClass().getClassLoader()) {
          DriverManager.deregisterDriver(d); // without this, the driver keeps the
      }                                      // old webapp classloader reachable forever
  }
  ```
- **Résolution :** Désenregistrer explicitement les drivers JDBC et vider les `ThreadLocal`s dans un shutdown hook,
  ou — la correction pragmatique que la plupart des équipes adoptent réellement — arrêter les hot redeploys et redémarrer le
  processus JVM à chaque déploiement, ce qui est de toute façon la pratique standard dans les déploiements
  à base de conteneurs.
- **Prévention :** Dans un monde conteneurisé, éviter entièrement le pattern de hot-redeploy — un processus
  par version déployée, remplacé en bloc, évite toute cette classe de fuites.

### S13. Sous charge, un service « singleton » est parfois construit plus d'une fois, causant des effets de bord en double
- **Symptômes :** Un composant censé être une instance partagée unique (par ex. l'initialisation d'un registre de métriques,
  l'ouverture d'un connection pool) logue parfois son message « initializing » deux fois sous charge
  de démarrage concurrent, et des symptômes de ressources en double s'ensuivent en aval (métriques enregistrées deux fois,
  connection pool doublé).
- **Diagnostic :** Vérifier l'implémentation du singleton pour le pattern double-checked-locking
  *sans* champ `volatile`, ou un `getInstance()` lazy sans aucune synchronisation — lors du premier accès
  concurrent, deux threads peuvent tous deux voir le champ à `null`, tous deux procéder à la
  construction d'une instance, et la seconde écriture écrase silencieusement la première (ou, sans
  `volatile`, un thread peut observer un objet partiellement construit à cause du réordonnancement d'instructions).
- **Exemple :**
  ```java
  class MetricsRegistry {
      private static MetricsRegistry instance; // missing volatile

      static MetricsRegistry getInstance() {
          if (instance == null) {
              synchronized (MetricsRegistry.class) {
                  if (instance == null) {
                      instance = new MetricsRegistry(); // reordering can publish a
                  }                                      // partially-constructed reference
              }
          }
          return instance;
      }
  }
  ```
- **Résolution :** Passer au pattern static-holder-class de Bill Pugh (Q19), dont la JVM
  garantit qu'il est thread-safe sans aucune synchronisation nécessaire, ou ajouter `volatile` si le double-checked
  locking doit être conservé pour une raison quelconque.
- **Prévention :** Adopter par défaut le pattern static-holder (ou un singleton `enum`) pour tout
  singleton fait main plutôt que le double-checked locking — c'est strictement plus simple et supprime
  toute cette classe de défaillances.

### S14. Les temps de pause GC se dégradent nettement juste après une mise à niveau du JDK/du collector
- **Symptômes :** Après la mise à niveau de la version du JDK (ou le changement de collector par défaut), la latence p99
  régresse alors que le débit et le CPU semblent similaires à avant.
- **Diagnostic :** Comparer les logs GC avant et après ; une cause courante est que les flags de dimensionnement du heap
  (`-Xmx`, `-Xms`, ratios de générations) réglés pour le comportement de l'ancien collector ne se transposent pas
  proprement aux défauts du nouveau — par ex. la taille de région de G1 et l'objectif de temps de pause interagissent
  différemment avec une taille de heap donnée que le collector qu'il a remplacé.
- **Exemple :**
  ```
  # Old flags, tuned for an older collector's defaults, carried over verbatim:
  -Xmx4g -XX:NewRatio=2 -XX:MaxGCPauseMillis=500
  # New collector's own recommended starting point, re-tuned instead of copied:
  -Xmx4g -XX:MaxGCPauseMillis=100
  ```
- **Résolution :** Re-régler à partir du point de départ recommandé par le collector lui-même plutôt que de
  reporter les anciens flags tels quels ; définir un objectif `-XX:MaxGCPauseMillis` explicite correspondant au
  SLO réel et laisser G1 (ou le nouveau collector) adapter le dimensionnement des régions pour l'atteindre, puis mesurer de nouveau
  sous charge représentative.
- **Prévention :** Traiter un changement de collector ou de version majeure du JDK comme un
  déploiement sensible à la performance exigeant un test de charge et une comparaison de logs GC avant d'atteindre la production, et non un
  simple bump de dépendance de routine.

### S15. Les `NullPointerException`s explosent juste après la mise à niveau d'une dépendance de bibliothèque
- **Symptômes :** Un service auparavant stable commence à lever des `NullPointerException` à plusieurs
  endroits d'appel sans rapport immédiatement après le bump de version d'une dépendance, sans aucun changement de code
  applicatif.
- **Diagnostic :** Vérifier le changelog de la dépendance pour une méthode qui retournait auparavant une sentinelle
  (une collection vide, une chaîne vide) et retourne maintenant `null` dans certains cas, ou — de plus en plus
  courant — une méthode qui a changé son type de retour en `Optional<T>`, et des appelants qui faisaient un
  accès direct à un champ/une méthode sur l'ancien type de retour appellent maintenant directement à travers l'enveloppe
  `Optional` ou la déballent incorrectement (`.get()` sans vérifier `.isPresent()`).
- **Exemple :**
  ```java
  // Old library version: findById returned User, or null if not found.
  User user = repository.findById(id);
  user.getEmail(); // worked fine — call sites already null-checked `user` where needed

  // New library version: findById now returns Optional<User> instead.
  Optional<User> maybeUser = repository.findById(id);
  maybeUser.get().getEmail(); // .get() without .isPresent() throws NoSuchElementException,
                              // or a lazy caller casts/ignores the change and gets an NPE
                              // from treating the Optional itself as the User
  ```
- **Résolution :** Corriger chaque site d'appel pour gérer correctement le nouveau contrat — un `Optional` doit être
  consommé avec `.map()`/`.orElse()`/`.ifPresent()`, et non avec un `.get()` appelé à l'aveugle ; figer la
  version de la dépendance en attendant la correction si le problème se propage plus vite qu'on ne peut le patcher.
- **Prévention :** Figer les versions des dépendances et relire les changelogs (en particulier les changements de type de retour/nullabilité)
  avant de les bumper, plutôt que de faire des mises à niveau automatiques ; activer un analyseur statique de vérification de nullabilité
  là où les conventions du codebase le permettent.

### S16. Le débit plafonne sous forte concurrence alors que le CPU a de la marge
- **Symptômes :** Ajouter plus de charge concurrente n'augmente pas le débit au-delà d'un certain point, et
  l'utilisation CPU reste bien en dessous de 100 % — le système n'est pas limité par le calcul, mais il ne
  passe pas non plus à l'échelle.
- **Diagnostic :** Thread dump sous charge ; chercher de nombreux threads `BLOCKED` (pas `WAITING` sur de l'I/O,
  spécifiquement `BLOCKED` à l'entrée d'un monitor) tous en file sur la même méthode `synchronized` — c'est de la
  contention de lock sur une section critique trop grossière, sérialisant du travail qui n'avait pas besoin
  de l'être.
- **Exemple :**
  ```java
  class RequestCounter {
      private long total = 0;
      private final Map<String, Object> unrelatedCache = new HashMap<>();

      synchronized void recordRequest(String endpoint) { // the whole method is one lock
          total++;
          unrelatedCache.computeIfAbsent(endpoint, k -> loadMetadata(k)); // slow, unrelated work
      }                                                                   // serialized behind
  }                                                                       // the same monitor
  ```
- **Résolution :** Réduire la section critique au seul état mutable réellement partagé (ne pas
  synchroniser toute la méthode si seule la mise à jour d'un compteur doit être protégée), passer à une
  structure à grain plus fin ou lock-free — ici, un `AtomicLong` pour `total` et une
  `ConcurrentHashMap` pour le cache supprime entièrement le lock partagé :
  ```java
  class RequestCounter {
      private final AtomicLong total = new AtomicLong();
      private final Map<String, Object> unrelatedCache = new ConcurrentHashMap<>();

      void recordRequest(String endpoint) {
          total.incrementAndGet();
          unrelatedCache.computeIfAbsent(endpoint, k -> loadMetadata(k));
      }
  }
  ```
  Si la ressource disputée est réellement une dépendance séquentielle unique partagée, c'est un vrai
  goulot d'étranglement architectural à repenser (par ex. en partitionnant la charge pour que différentes
  requêtes ne se disputent pas du tout le même lock).
- **Prévention :** Garder les blocs `synchronized` aussi petits que possible par défaut, et tester en charge le nouveau
  code à état partagé sous une concurrence réaliste avant sa livraison — ce mode de défaillance n'apparaît souvent pas
  avant que le trafic n'atteigne l'échelle de production.

### S17. La latence grimpe à plusieurs minutes pendant un ralentissement aval, puis le service meurt avec `OutOfMemoryError`
- **Symptômes :** Un service de notification de paiement répond normalement en 40 ms. Quand une API partenaire
  se met à répondre en 3 s au lieu de 100 ms, le p99 de *notre* endpoint dépasse 60 s en quelques
  minutes — bien après que le partenaire a récupéré — et finalement les pods sont OOMKilled. Le CPU est bas
  tout du long, et le nombre de threads ne grossit jamais.
- **Diagnostic :** CPU bas plus nombre de threads plat signifie que le travail *attend*, sans s'exécuter. Un thread
  dump (`jcmd <pid> Thread.print`, pris deux fois à ~10 s d'intervalle) montre les 8 threads du pool bloqués dans le
  même appel HTTP partenaire. L'indice est la file : exposer
  `ThreadPoolExecutor.getQueue().size()` (ou `ExecutorServiceMetrics` de Micrometer, c'est-à-dire
  `executor.queued`) montre des centaines de milliers et en croissance, et un histogramme du heap
  (`jmap -histo:live <pid>`) est dominé par des instances de `FutureTask` / lambda. La cause est
  `Executors.newFixedThreadPool(8)` : sa file est une `LinkedBlockingQueue` *non bornée*, donc il ne
  dit jamais « non » — chaque tâche soumise attend son tour derrière tout ce qui la précède, ce qui transforme un
  ralentissement transitoire en minutes de latence puis en épuisement du heap (Q21).
- **Exemple :**
  ```java
  // The unbounded queue is the hidden default — no back-pressure anywhere.
  ExecutorService pool = Executors.newFixedThreadPool(8);
  void onPayment(Payment p) { pool.submit(() -> partner.notify(p)); }  // always accepted
  ```
- **Résolution :** Atténuer d'abord : délester la charge ou scaler horizontalement, et redémarrer pour vider la file. Correction de fond —
  une file bornée avec une politique de rejet explicite, plus un timeout sur l'appel partenaire pour qu'une
  dépendance lente ne puisse pas retenir un thread indéfiniment :
  ```java
  ThreadPoolExecutor pool = new ThreadPoolExecutor(
      8, 8, 0L, TimeUnit.SECONDS,
      new ArrayBlockingQueue<>(200),                    // bounded: ~200 waiting tasks max
      new ThreadPoolExecutor.CallerRunsPolicy());       // or AbortPolicy -> return 503 upstream
  ```
  `CallerRunsPolicy` ralentit le producteur (back-pressure naturelle) ; `AbortPolicy` échoue rapidement pour que
  l'appelant puisse réessayer ou dégrader. Vérifier en rejouant le ralentissement du partenaire lors d'un test de charge
  (retarder le stub à 3 s) et en contrôlant que la latence atteint un plateau, que la file reste à son plafond, et que
  le heap reste plat.
- **Prévention :** Interdire `Executors.newFixedThreadPool`/`newCachedThreadPool` en code review au profit
  d'un `ThreadPoolExecutor` explicite (ou d'un bean partagé et configuré) ; alerter sur la profondeur de file et le
  temps d'attente des tâches, pas seulement sur le CPU ; chaque appel sortant reçoit un timeout (connect + read).

### S18. Les dates sont parfois fausses, ou le parsing lève de bizarres `NumberFormatException`s, uniquement sous charge
- **Symptômes :** Un job d'import et une API partagent un utilitaire qui formate et parse des dates.
  Parfois une facture est estampillée avec la date d'une *autre* ligne, et les logs montrent
  `NumberFormatException: multiple points`, `ArrayIndexOutOfBoundsException`, ou
  `NumberFormatException: For input string: ""`. Cela ne se reproduit jamais avec une seule requête.
- **Diagnostic :** Des erreurs bizarres, non déterministes et *corrélées à la charge* sont la
  signature d'un état mutable partagé. Faire un grep de `SimpleDateFormat` (et `DecimalFormat`,
  `NumberFormat`) dans un champ `static final` — ils contiennent un `Calendar` interne et des buffers de travail
  réécrits à chaque appel, donc deux threads appelant `format()`/`parse()`
  concurremment corrompent l'état intermédiaire l'un de l'autre. `SimpleDateFormat` est documenté comme non
  thread-safe ; le bug n'apparaît que lorsque deux appels se chevauchent réellement (Q15).
- **Exemple :**
  ```java
  class DateUtil {
      static final SimpleDateFormat FMT = new SimpleDateFormat("yyyy-MM-dd"); // shared, mutable
      static String format(Date d) { return FMT.format(d); }                 // racy
  }
  ```
- **Résolution :** Le remplacer par l'API `java.time`, immuable et thread-safe — un seul
  `DateTimeFormatter` partagé convient :
  ```java
  static final DateTimeFormatter FMT = DateTimeFormatter.ISO_LOCAL_DATE;
  static String format(LocalDate d) { return FMT.format(d); }
  ```
  Si un appelant legacy doit garder `SimpleDateFormat`, créer une nouvelle instance par appel (assez peu coûteux)
  plutôt que d'ajouter `synchronized`, qui sérialise chaque opération de date de l'application. Vérifier avec
  un test qui martèle la méthode depuis 32 threads pendant quelques secondes et vérifie que chaque résultat
  correspond à une baseline mono-thread.
- **Prévention :** Ajouter une règle d'analyse statique qui signale un `SimpleDateFormat`/`Calendar` `static`
  (vérifications Error Prone `JdkObsolete`/`SimpleDateFormat`, SonarQube), et standardiser sur `java.time`.

### S19. Le pod est OOMKilled alors que le dashboard du heap n'en montre qu'environ 40 % utilisé
- **Symptômes :** Une gateway basée sur Netty avec `-Xmx2g` dans un conteneur de 3 GiB redémarre toutes les quelques
  heures avec `OOMKilled` (exit 137, Kubernetes affiche `Reason: OOMKilled`). Pas d'
  `OutOfMemoryError` dans les logs, aucun heap dump écrit, et le graphe du heap est confortablement
  en dessous de la limite à chaque redémarrage.
- **Diagnostic :** Le kernel a tué le *processus* pour dépassement de la limite du conteneur, qui compte
  tout ce que la JVM mappe — pas seulement le heap. Comparer le RSS du conteneur au heap : un grand écart signifie
  de la mémoire native. Activer le Native Memory Tracking (`-XX:NativeMemoryTracking=summary`) et exécuter
  `jcmd <pid> VM.native_memory summary`, en comparant deux snapshots avec `summary.diff` ; la
  catégorie qui grossit est ici *Other/Internal* — les **`ByteBuffer`s directs**. Les direct buffers ne sont récupérés que
  quand leurs petits objets wrapper Java sont collectés par le GC, donc avec un grand heap inactif le GC
  s'exécute rarement et la mémoire off-heap derrière les buffers non référencés s'accumule jusqu'au plafond
  du conteneur. Autres consommateurs natifs à écarter avec le même outil : Metaspace (S12), stacks de threads
  (nombre de `Thread` × `-Xss`), et le code cache.
- **Exemple :**
  ```java
  // Off-heap allocation whose lifetime is tied to a tiny on-heap wrapper.
  ByteBuffer buf = ByteBuffer.allocateDirect(8 * 1024 * 1024);  // 8 MiB, invisible to -Xmx
  // Thousands of these per minute + a heap that rarely needs collecting = native growth.
  ```
- **Résolution :** Le plafonner et le budgéter : définir `-XX:MaxDirectMemorySize` explicitement, et dimensionner le
  conteneur comme heap + Metaspace + direct + (threads × stack) + ~10–20 % de marge, plutôt que de
  régler `-Xmx` près de la limite du conteneur. Préférer `-XX:MaxRAMPercentage=60` à un
  `-Xmx` codé en dur pour que le heap s'adapte au conteneur. Poolér et réutiliser les buffers (le
  `PooledByteBufAllocator` de Netty) au lieu d'allouer par requête. Vérifier que le RSS atteint maintenant un plateau lors d'un
  soak test de plusieurs heures.
- **Prévention :** Mettre le *RSS du conteneur* et les pools non-heap de la JVM (`jvm.buffer.memory.used`,
  Metaspace) sur un dashboard à côté du heap ; activer NMT dans un soak test de staging ; documenter la formule du budget mémoire dans le
  runbook du service.

### S20. Un job planifié se déclenche une heure trop tôt, deux fois, ou pas du tout le week-end du changement d'heure
- **Symptômes :** Un job de règlement quotidien à 02:30 et une fonctionnalité « expire dans 24 heures » fonctionnent toute l'année,
  puis le dernier dimanche de mars il ne s'exécute pas du tout, et le dernier dimanche d'octobre il
  s'exécute deux fois. Des clients d'une région voient aussi des heures d'expiration décalées d'une heure.
- **Diagnostic :** Corréler les dates de l'incident avec les transitions DST — un indice fort en soi.
  Puis chercher `LocalDateTime` utilisé pour représenter un *instant* ou pour ajouter des durées :
  `LocalDateTime` n'a pas de zone, donc il ne peut pas savoir que 02:30 n'existe pas la nuit du passage à l'heure d'été
  (l'horloge saute de 02:00 à 03:00) ou existe deux fois la nuit du retour à l'heure d'hiver. Chercher aussi
  « 24 heures » implémenté avec `plusDays(1)` vs `plus(Duration.ofHours(24))`, qui diffèrent d'une
  heure à travers une transition.
- **Exemple :**
  ```java
  ZoneId paris = ZoneId.of("Europe/Paris");

  // Gap: 02:30 does not exist on 2026-03-29 in Paris; java.time silently shifts it forward.
  ZonedDateTime gap = LocalDateTime.of(2026, 3, 29, 2, 30).atZone(paris);   // 03:30+02:00

  // "24 hours later" vs "the same wall-clock time tomorrow":
  ZonedDateTime day = ZonedDateTime.of(2026, 3, 28, 12, 0, 0, 0, paris);
  day.plusDays(1);                     // 2026-03-29T12:00+02:00 — same wall-clock time
  day.plus(Duration.ofHours(24));      // 2026-03-29T13:00+02:00 — exactly 24 elapsed hours
  ```
- **Résolution :** Décider pour chaque champ s'il s'agit d'un **instant** ou d'une **règle d'heure murale**. Stocker et
  comparer les instants en `Instant`/UTC (`timestamptz` dans PostgreSQL). Pour « chaque jour à 02:30
  heure locale », conserver la règle (`LocalTime` + `ZoneId`) et *calculer* chaque occurrence avec
  `ZonedDateTime`, en gérant explicitement le gap (exécuter au premier instant valide) et l'overlap
  (exécuter une seule fois — choisir l'offset le plus tôt via `ZonedDateTime.withEarlierOffsetAtOverlap()`), ou
  planifier le job en UTC s'il n'a pas à suivre l'heure locale. Vérifier avec des tests qui injectent
  une `Clock` fixe pour les deux dates de transition et les deux sens.
- **Prévention :** Convention : `Instant` pour les événements, `ZonedDateTime` pour les planifications côté utilisateur,
  `LocalDateTime` uniquement pour les données sans signification de zone (un datetime de type anniversaire). Injecter
  `java.time.Clock` au lieu d'appeler `now()` pour que les tests du jour de DST soient triviaux, et garder les dates DST
  de chaque région d'exploitation dans la suite de tests.

### S21. Un job de « nettoyage » dit avoir supprimé les sessions expirées, pourtant la mémoire continue de croître et des sessions périmées apparaissent encore
- **Symptômes :** Un `HashSet<Session>` suit les sessions actives. Une tâche planifiée appelle
  `remove()` sur les expirées et logue `removed=true`, mais le `size()` du set continue de monter, l'usage du heap
  grimpe régulièrement, et certains utilisateurs sont encore traités comme connectés après déconnexion. Aucune exception
  nulle part.
- **Diagnostic :** `size()` grossit alors que `remove()` ne réussit que pour *certains* éléments, donc
  suspecter le hashing : un élément qui ne peut plus être retrouvé par son propre hash. Un heap dump montre le
  set contenant bien plus d'objets `Session` que n'en justifie toute logique métier ; itérer et
  appeler `set.contains(each)` dessus renvoie `false` pour beaucoup. C'est le motif de la Q12 —
  `hashCode()` inclut un champ mutable (`state`, `lastSeen`) qui a changé *après* l'insertion, donc
  l'entrée se trouve dans le mauvais bucket et `contains` comme `remove` la ratent.
- **Exemple :**
  ```java
  Set<Session> active = new HashSet<>();
  active.add(session);                // hashed with state = "OPEN"
  session.state = "EXPIRED";          // mutated while inside the set
  active.remove(session);             // false — looks in the "EXPIRED" bucket, entry is orphaned
  ```
- **Résolution :** Immédiat : reconstruire le set (`new HashSet<>(old)` re-hashe chaque élément avec
  ses champs actuels) ou le vider via `iterator().remove()` / `removeIf`, qui parcourent les buckets
  au lieu de hasher. Correction de fond : faire dépendre l'identité uniquement de données immuables — implémenter
  `equals`/`hashCode` sur l'id de session, ou indexer une `Map<SessionId, Session>` et garder l'état mutable
  dans la valeur. Vérifier avec un test unitaire qui mute l'état après insertion et vérifie que
  `contains`/`remove` réussissent toujours, et contrôler que le heap atteint un plateau après le déploiement.
- **Prévention :** Préférer des `record`s ou des classes à champs `final` comme clés ; une règle de code review pratique —
  si une classe est utilisée dans un `HashSet` ou comme clé de `HashMap`, chaque champ de `hashCode()` doit être
  `final`. Certains analyseurs statiques (vérifications de type `MutableKey` d'Error Prone) peuvent l'imposer.

### S22. Le service se bloque au démarrage environ un déploiement sur vingt, sans erreur et sans usage CPU
- **Symptômes :** Après un déploiement, une instance reste « starting » pour toujours : la readiness probe ne
  passe jamais, le CPU est proche de 0, et les logs s'arrêtent en plein démarrage sans exception. Redémarrer le pod règle le problème,
  ce qui en fait une légende de déploiement instable plutôt qu'un ticket. Cela arrive plus souvent quand
  l'instance démarre avec plus de CPU disponibles (plus de threads de démarrage parallèles).
- **Diagnostic :** Prendre deux thread dumps (`jcmd <pid> Thread.print`) à quelques secondes d'intervalle et les comparer.
  Deux threads applicatifs sont bloqués avec la frame `at com.acme.Catalog.<clinit>` /
  `at com.acme.Pricing.<clinit>`, chacun attendant que la classe de l'autre finisse de s'initialiser.
  `<clinit>` est l'indice : c'est le deadlock d'initialisation de classe de la Q18, et le rapport standard de la JVM
  « Found one Java-level deadlock » ne le liste souvent *pas*, donc un rapport vide n'est
  pas une preuve d'innocence. Il est intermittent parce qu'il exige que les deux classes soient touchées en premier par deux threads de
  démarrage parallèles (par ex. un initialiseur de beans parallèle) dans la même fenêtre.
- **Exemple :**
  ```java
  class Catalog { static final Pricing PRICING = new Pricing(); /* ... */ }
  class Pricing { static final Catalog CATALOG = new Catalog(); /* needs Catalog.<clinit> to finish */ }
  // Thread 1 initializes Catalog, needs Pricing; thread 2 initializes Pricing, needs Catalog.
  ```
- **Résolution :** Casser le cycle pour qu'aucun static initializer ne dépende de l'initialisation d'une autre
  classe : rendre un côté lazy (un holder Bill Pugh, Q19) ou injecter la dépendance à l'exécution
  au lieu de la résoudre dans un bloc `static` ; sortir tout I/O ou câblage de `<clinit>`. En
  palliatif, forcer un ordre d'initialisation fixe au démarrage depuis un seul thread (toucher `Catalog`
  avant de démarrer le travail parallèle). Vérifier en exécutant le démarrage 200 fois en boucle dans la CI avec
  l'init parallèle activée — un deadlock qui apparaît 1 fois sur 20 se manifestera en quelques exécutions.
- **Prévention :** Les static initializers doivent être triviaux : constantes et construction pure uniquement, pas de
  références statiques inter-classes en cycle, pas de threads, pas d'I/O. Ajouter un test de watchdog de démarrage qui
  échoue si l'application n'est pas prête dans une limite donnée, et capturer un thread dump automatiquement quand
  la readiness expire pour que la prochaine occurrence s'explique d'elle-même.

## 📌 Cheat-sheet

- **Chaîne de collisions `HashMap`** → arbre dès qu'un bucket a >8 entrées et que la table a ≥64 buckets, retour en liste sous 6 entrées ; un mauvais `hashCode()` dégrade O(1) vers O(log n) — mais un contrat `equals()`/`hashCode()` rompu *duplique* silencieusement les clés, ce qui est pire que lent.
- **`ConcurrentModificationException`** → itérateur fail-fast + `modCount` ; corriger avec `Iterator.remove()`/`removeIf`, pas avec un remove-pendant-l'itération manuel ni un contournement par index.
- **Singleton, classé :** `enum` (le meilleur — bloque aussi les attaques par réflexion/désérialisation) ≈ static holder de Bill Pugh (le meilleur quand ce ne peut pas être un enum) > double-checked locking avec `volatile` > accesseur synchronized > `static final` eager.
- **`synchronized`** = exclusion mutuelle + une arête happens-before (visibilité de tout ce qui précède le relâchement du lock). **`volatile`** = visibilité seulement, pas d'atomicité pour les opérations composées comme `i++`.
- **GC roots** : locales de stack, champs statiques, références JNI — accessibilité, pas comptage de références ; les cycles ne sont pas des fuites.
- **Virtual threads** = bon marché, gérés par la JVM, démontés sur I/O bloquant — mais `synchronized` autour d'I/O épingle le carrier thread, et une habitude de `ThreadLocal` inoffensive à l'échelle des platform threads ne l'est pas à l'échelle des virtual threads.
- **Piège du common pool** : `parallelStream()` et les `CompletableFuture` async par défaut partagent un unique `ForkJoinPool.commonPool()` à l'échelle de la JVM — un appel bloquant dans l'un ou l'autre peut affamer du code sans rapport ailleurs dans le processus.
- **`thenCompose` vs `thenApply`** : utiliser `thenCompose` quand l'étape suivante retourne elle-même un `CompletableFuture`, sinon on obtient un future imbriqué par erreur.
- **Cache d'`Integer`** : -128..127 est *spécifié*, pas une coïncidence — `==` « marche » par contrat dans cette plage, casse (aussi par contrat) en dehors ; toujours utiliser `.equals()` ou unboxer.
- **try-with-resources** ferme dans l'ordre inverse ; l'exception du bloc try l'emporte, l'exception de `close()` est rattachée comme suppressed — un bloc `finally` écrit à la main perd souvent silencieusement l'une des deux.
- **Exceptions checked** = conditions récupérables imposées par le compilateur ; **unchecked** = erreurs de programmation. `catch (Exception e) {}` est l'anti-pattern que ces deux conceptions cherchent à empêcher.
- **Type erasure** casse : la surcharge par paramètre générique, la création de tableau générique, `instanceof ParameterizedType` — le compilateur rafistole le polymorphisme autour avec des bridge methods synthétiques.
- **Sealed + pattern matching de switch** = exhaustivité vérifiée par le compilateur — mais ajouter une branche `default` défensive jette cette garantie.
- **Fuite malgré le GC** = accessibilité involontaire : collections statiques, listeners non retirés, `ThreadLocal` non vidé sur des threads poolés (pire à l'échelle des virtual threads).
- **`StackOverflowError`** = région stack, récursion non bornée. **`OutOfMemoryError`** = région heap/metaspace/native-thread — lire le message après les deux-points ; relever `-Xmx`/`-Xss` retarde, sans le corriger, un algorithme réellement non borné.
- **Collectors :** G1 = défaut sûr, objectif de pause ajustable. ZGC/Shenandoah = concurrents, pauses sub-ms plates quelle que soit la taille du heap, un certain coût CPU/débit — choisir selon le SLO de latence réel du service, pas selon la réputation.
- **Clés de hash mutables** : un champ utilisé dans `hashCode()` qui change après l'insertion orpheline l'entrée — `contains`/`remove` la ratent, elle fuit ; indexer sur des ids/records immuables.
- **`Optional`** : un *type de retour* uniquement (pas champ/paramètre) ; `orElse(x)` évalue `x` de façon eager, `orElseGet` de façon lazy ; `get()` ne fait que déplacer l'exception — utiliser `orElseThrow`/`map`/`flatMap`.
- **Streams** : lazy jusqu'à une opération terminale, à usage unique, ne jamais muter d'état partagé depuis `parallel().forEach` ; `Stream.toList()` est non modifiable, `Collectors.toMap` lève sur clés dupliquées sans merge function.
- **Safe publication** : pas de happens-before = un autre thread peut voir la référence mais des valeurs de champs par défaut ; utiliser `volatile`/`final`/init statique/locks, et ne jamais laisser fuiter `this` depuis un constructeur.
- **`ThreadLocal` vs `ScopedValue`** : `ThreadLocal` est mutable et sans portée (fuit sur les threads poolés, lourd à l'échelle des virtual threads) ; `ScopedValue` (final en JDK 25) est immuable, borné, nettoyé automatiquement.
- **`ReentrantLock`/`StampedLock`** : à choisir pour les timeouts de `tryLock`, l'interruptibilité, plusieurs `Condition`s, les lectures optimistes — toujours `unlock()` dans `finally` ; `StampedLock` n'est pas réentrant. Le pinning de virtual threads par `synchronized` a été en grande partie supprimé dans JDK 24.
- **Deadlock d'initialisation de classe** : des static initializers cycliques entre threads se bloquent dans `<clinit>` (souvent invisibles au détecteur de deadlock) ; un initialiseur en échec empoisonne la classe (`NoClassDefFoundError` ensuite) — lire la *première* erreur.
- **Argent** : jamais `double` ; `BigDecimal` depuis `String`/`valueOf`, `compareTo` et non `equals` (scale), `divide` exige un scale/`MathContext`, le mode d'arrondi (`HALF_EVEN` vs `HALF_UP`) et le *point* d'arrondi sont des règles métier.
- **File d'executor non bornée** (`newFixedThreadPool`) = pas de back-pressure : la latence grimpe pendant des minutes, puis OOM — utiliser un `ThreadPoolExecutor` borné + politique de rejet + timeouts.
- **`SimpleDateFormat`/`DecimalFormat` partagé** = sortie corrompue sous charge — utiliser les formatters immuables de `java.time`.
- **OOMKilled avec un heap sain** = mémoire native (direct buffers, Metaspace, stacks de threads) : budgéter heap + non-heap dans la limite du conteneur, utiliser NMT (`jcmd VM.native_memory`).
- **DST** : `LocalDateTime` n'a pas de zone — gaps et overlaps cassent les planifications en heure murale ; stocker `Instant`, calculer les planifications locales avec `ZonedDateTime`, injecter une `Clock` pour les tests.
