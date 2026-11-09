# Java Core & JVM

## 🟢 Fondamentaux

### POO & bases du langage

#### Q1. Interface vs classe abstraite — comment choisir ? {#interface-abstract-class}
**Réponse :** Une **interface** définit une capacité ou un contrat que promet un type (`Comparable`,
`PaymentGateway`). Une classe peut en implémenter plusieurs, et depuis Java 8 les interfaces peuvent porter des
méthodes `default` et `static`, mais aucun état d'instance. Une **classe abstraite** est une implémentation partielle
partagée par une famille de types proches : elle peut avoir des champs, des constructeurs et des helpers `protected`,
et une classe ne peut en étendre qu'une. Choisissez l'interface par défaut, car elle laisse les implémentations libres
d'étendre autre chose et se simule facilement en test. Utilisez une classe abstraite quand les sous-classes partagent
réellement un état et un squelette d'algorithme fixe (Template Method), et gardez la hiérarchie peu profonde. Depuis
Java 17, une **interface sealed** avec des records est souvent meilleure que les deux pour un ensemble fermé de
variantes.

**Exemple :**

```java
public interface PaymentGateway {              // contrat : nombreuses implémentations sans lien
    PaymentResult charge(Money amount, CardToken card);
}

public abstract class BaseImporter {           // état partagé + squelette fixe
    protected final Clock clock;
    protected BaseImporter(Clock clock) { this.clock = clock; }
    public final ImportReport run(Path file) { var rows = parse(file); return store(validate(rows)); }
    protected abstract List<Row> parse(Path file);
    // validate() et store() partagés par tous les importeurs
}
```

**Piège : conflit de méthodes `default`.** Si une classe implémente deux interfaces qui fournissent la même méthode
`default`, elle doit la redéfinir et choisir explicitement.

```java
interface Entity    { default String label() { return "entity"; } }
interface Auditable { default String label() { return "audited"; } }

class Account implements Entity, Auditable {
    @Override public String label() {
        return Auditable.super.label();      // choix explicite ; sans cela : erreur de compilation
    }
}
```

#### Q2. Quelle est la différence entre `==` et `.equals()` ? {#double-equals-vs-equals}
**Réponse :** `==` compare ce que les variables *contiennent* : pour les primitifs c'est la valeur, pour les références
c'est l'identité de l'objet (les deux variables pointent-elles vers exactement le même objet du tas ?). `.equals()` est
une méthode qui demande à l'objet s'il se considère *logiquement* égal à un autre. `Object.equals()` se comporte par
défaut comme `==`, donc une classe qui ne la redéfinit pas a une sémantique d'identité ; `String`, les types enveloppes,
`List`, `Set`, `LocalDate` et les records la redéfinissent pour comparer le contenu. Règle pratique : `==` pour les
primitifs, les enums et les tests de `null` ; `.equals()` (ou `Objects.equals(a, b)` quand `a` peut être `null`) pour le
reste. Placez toujours l'opérande non nul connu à gauche (`"PAID".equals(status)`) ou utilisez `Objects.equals` pour
éviter une `NullPointerException`.

**Exemple :**

```java
String a = new String("rdv");
String b = new String("rdv");
System.out.println(a == b);        // false : deux objets différents
System.out.println(a.equals(b));   // true : mêmes caractères
System.out.println(a == "rdv");    // false : le littéral "rdv" vit dans le pool de chaînes
System.out.println(a.intern() == "rdv"); // true, mais ne bâtissez pas de logique dessus

record Slot(String doctorId, LocalDateTime start) {}
new Slot("d1", t).equals(new Slot("d1", t)); // true : un record génère equals sur tous ses composants
```

**Pourquoi c'est un piège :** les littéraux de chaîne sont mis en pool, donc `"a" == "a"` vaut `true` et un test rapide
donne l'impression que `==` est correct, jusqu'à ce qu'une valeur vienne d'une saisie, d'une base de données ou de
`new String(...)` et que la comparaison échoue silencieusement en production. C'est pareil avec les nombres encapsulés
(voir [Java Q26](java-core-jvm.md#autoboxing-trap-integer)). Et redéfinir `equals` sans `hashCode` casse les collections à hachage
(voir [Java Q3](java-core-jvm.md#equals-hashcode-contract-breaks-override)).

#### Q3. Quel est le contrat `equals`/`hashCode`, et que se passe-t-il si on n'en redéfinit qu'un ? {#equals-hashcode-contract-breaks-override}
**Réponse :** Si `a.equals(b)` est vrai, alors `a.hashCode() == b.hashCode()` doit aussi être vrai. Des hash codes
égaux n'impliquent pas l'égalité (les collisions sont permises). `equals` doit être réflexive, symétrique, transitive,
cohérente et renvoyer false pour `null`. Redéfinir `equals` sans `hashCode` casse les collections à hachage : deux
objets « égaux » tombent dans des buckets différents, donc `set.contains(copie)` renvoie false et un `HashSet` accepte
des doublons. Basez les deux méthodes sur les mêmes champs immuables. Les records génèrent les deux à partir de tous
leurs composants. Pour ce que cela donne à l'intérieur d'une `HashMap`, voir Q18 et Q19.

**Exemple :**

```java
class Email {
    private final String value;
    Email(String v) { value = v.toLowerCase(); }
    @Override public boolean equals(Object o) { return o instanceof Email e && value.equals(e.value); }
    // hashCode() manquant !
}
Set<Email> set = new HashSet<>(List.of(new Email("a@x.io")));
set.contains(new Email("A@x.io"));   // false — hash d'identité différent, mauvais bucket
```

#### Q4. Que signifient `final` et `static` sur une variable, une méthode et une classe ? {#final-static-variable-method-class}
**Réponse :** Variable `final` : affectée exactement une fois. Pour une référence, la référence ne peut pas changer,
mais l'objet pointé le peut encore (`final List` n'est pas une liste immuable). Méthode `final` : ne peut pas être
redéfinie. Classe `final` : ne peut pas être étendue (`String`, records). `static` signifie que le membre appartient à
la **classe**, pas à une instance : une seule copie partagée par toutes les instances, accessible sans objet.
`static final` avec une valeur immuable est une constante. Attention à **l'état statique mutable** : il est partagé
entre threads et entre tests, survit d'une classe de test à l'autre dans la même JVM, et cause souvent fuites et tests
instables.

**Exemple :**

```java
final List<String> names = new ArrayList<>();
names.add("Ada");                 // ok : la liste est mutable
// names = new ArrayList<>();     // erreur de compilation : la référence est final
static final List<String> ROLES = List.of("ADMIN", "USER");   // une vraie constante : valeur immuable
```

**Méthode `static` en détail :** une méthode `static` appartient à la classe, pas à une instance : elle n'a ni `this` ni
`super`. Elle ne peut donc pas accéder **directement** aux champs et méthodes d'instance, mais elle peut tout à fait les
utiliser **via une référence d'objet**. Formulation à éviter, trop forte : « une méthode static ne peut contenir que des
attributs static et appeler des méthodes static ».

```java
class Counter {
    private int value;                 // membre d'instance
    private static int created;        // membre de classe

    static Counter create() {
        created++;                     // OK : membre static
        // value++;                    // erreur : quel objet ? il n'y a pas de this
        Counter c = new Counter();
        c.value = 10;                  // OK : accès via une référence explicite
        return c;
    }

    void inc() {
        value++;
        created++;                     // une méthode d'instance voit aussi les membres static
    }
}
```

**Pièges :**
- Une méthode `static` n'est **pas redéfinie** mais **masquée** : l'appel dépend du type déclaré, pas du type réel (voir
  l'exemple `Printer.kind()` dans la question sur la surcharge et la redéfinition).
- `counter.create()` compile (avec un avertissement) mais appelle bien la méthode de classe : écrire `Counter.create()`.
- Un champ `static` mutable est un état global partagé entre threads : à éviter, ou à protéger.

**Usage réel :** fabriques (`List.of`, `Optional.of`, `Money.of`), utilitaires sans état (`Math`, `Objects`,
`Collections`), constantes `static final`.

#### Q5. Qu'est-ce qu'un bloc `static`, et quand s'exécute-t-il ? {#static-block-init-order}
**Réponse :** Un bloc `static { ... }` est exécuté **une seule fois**, à l'initialisation de la classe, c'est-à-dire à sa
première utilisation active : `new`, appel d'une méthode `static`, lecture d'un champ `static` non constant,
`Class.forName(...)`, ou initialisation d'une sous-classe. Il sert à initialiser des champs `static` qui demandent plus
qu'une expression. Ordre à retenir : **static parent → static enfant**, puis à chaque `new` : **instance parent →
constructeur parent → instance enfant → constructeur enfant**. Dans une classe, champs `static` et blocs `static`
s'exécutent dans l'ordre du fichier.

**Exemple :**

```java
class Parent {
    static { System.out.println("1. static Parent"); }
    { System.out.println("3. bloc d'instance Parent"); }
    Parent() { System.out.println("4. constructeur Parent"); }
}

class Child extends Parent {
    static { System.out.println("2. static Child"); }
    { System.out.println("5. bloc d'instance Child"); }
    Child() { System.out.println("6. constructeur Child"); }
}

new Child();   // 1, 2, 3, 4, 5, 6
new Child();   // 3, 4, 5, 6 : les blocs static ne repassent jamais

class Rates {
    static final Map<String, BigDecimal> FX;
    static {
        Map<String, BigDecimal> m = new HashMap<>();
        m.put("USD", new BigDecimal("1.0850"));
        m.put("GBP", new BigDecimal("0.8420"));
        FX = Map.copyOf(m);            // immuable une fois publié
    }
}
```

**Pièges :**
- Si le bloc lève une exception : `ExceptionInInitializerError` au premier accès, puis `NoClassDefFoundError` à **chaque**
  accès suivant. La classe est inutilisable jusqu'au redémarrage (voir [Java Q45](java-core-jvm.md#class-initialization-itself-deadlock-static)).
- Lire une constante de compilation (`static final String NAME = "x"`) ne déclenche pas l'initialisation : la valeur est
  recopiée par le compilateur.
- L'initialisation est thread-safe (verrou de la JVM), c'est ce qu'exploite le *holder idiom* du Singleton. Mais deux
  classes qui s'initialisent mutuellement depuis deux threads peuvent se bloquer.

**Usage réel :** charger un driver JDBC (historique : `Class.forName`), remplir une table de correspondance, enregistrer
des plugins. Aujourd'hui, on préfère souvent `Map.of(...)` ou un bean Spring.

#### Q6. Comment les modificateurs d'accès et les packages servent-ils l'encapsulation en pratique ? {#access-modifiers-packages-support-encapsulation}
**Réponse :** Quatre niveaux : `private` (la classe seule), package-private (sans mot-clé : même package), `protected`
(package plus sous-classes) et `public`. Utilisez la **visibilité la plus restreinte qui fonctionne** : champs privés,
helpers privés ou package-private, et seule la vraie API publique. Le package-private est sous-utilisé : dans une
organisation par fonctionnalité (`order/`, `payment/`), seuls la façade de service et les DTO doivent être publics, et
le repository et les classes internes restent package-private, pour que les autres packages ne puissent pas
contourner le service. Pour l'imposer entre modules, utilisez les `exports` JPMS (voir la section expert) ou des règles
ArchUnit.

**Les quatre niveaux en détail :**

| Modificateur | Même classe | Même package | Sous-classe (autre package) | Partout |
|---|:-:|:-:|:-:|:-:|
| `private` | oui | | | |
| *(défaut)* | oui | oui | | |
| `protected` | oui | oui | oui (par héritage) | |
| `public` | oui | oui | oui | oui |

```java
package com.bank.core;

public class Account {
    private BigDecimal balance;        // seulement Account
    String branchCode;                 // tout le package com.bank.core
    protected void audit() { }         // package + sous-classes, même ailleurs
    public BigDecimal balance() { return balance; }
}

package com.bank.savings;

class SavingsAccount extends Account {
    void close() {
        audit();                       // OK : accès hérité via this
        // new Account().audit();      // erreur : autre package, et pas via l'héritage
        // branchCode = "X";           // erreur : package-private
    }
}
```

**Pièges :**
- `protected` est **plus ouvert** que le défaut : il inclut tout le package. Beaucoup de candidats pensent « classe +
  sous-classes seulement ».
- Une classe de premier niveau ne peut être que `public` ou package-private. `private` et `protected` ne s'appliquent
  qu'aux membres et aux classes imbriquées.
- Une redéfinition ne peut pas réduire la visibilité : une méthode `public` reste `public` dans la sous-classe.
- Les modules (Java 9+) ajoutent un niveau au-dessus : une classe `public` d'un package non exporté reste invisible hors
  du module.

**Usage réel :** tout `private` par défaut, puis ouvrir au besoin. Le package-private est idéal pour les classes
d'implémentation et pour tester sans tout rendre `public`.

#### Q7. Quels sont les quatre piliers de la POO ? {#four-pillars-oop}
**Réponse :** **Encapsulation** (l'état n'est modifié que par des méthodes qui valident), **abstraction** (le contrat, pas
le comment), **héritage** (le code commun est écrit une fois) et **polymorphisme** (un seul appel, l'implémentation est
choisie à l'exécution). À l'entretien, donner un exemple de code pour chacun.

**Exemple :**

```java
interface PaymentMethod {                         // abstraction : le contrat, pas le comment
    BigDecimal fee(BigDecimal amount);
}

final class Account {                             // encapsulation : l'état ne change que via des méthodes qui valident
    private BigDecimal balance = BigDecimal.ZERO;
    void deposit(BigDecimal amount) {
        if (amount.signum() <= 0) throw new IllegalArgumentException("montant <= 0");
        balance = balance.add(amount);
    }
    BigDecimal balance() { return balance; }
}

abstract class Card implements PaymentMethod {    // héritage : le code commun est écrit une fois
    protected abstract BigDecimal rate();
    public BigDecimal fee(BigDecimal amount) { return amount.multiply(rate()); }
}
class Visa extends Card { protected BigDecimal rate() { return new BigDecimal("0.015"); } }
class Amex extends Card { protected BigDecimal rate() { return new BigDecimal("0.025"); } }

// polymorphisme : un seul appel, l'implémentation est choisie à l'exécution
for (PaymentMethod p : List.of(new Visa(), new Amex())) System.out.println(p.fee(amount));
```

**Pourquoi c'est un piège :** l'encapsulation ne se résume pas à des getters/setters. Un setter public sur `balance`
ruine l'invariant.

#### Q8. Surcharge vs redéfinition : quelle différence ? {#overloading-vs-overriding}
**Réponse :** La **surcharge** (*overloading*) est résolue à la **compilation**, d'après la signature et le type
**statique** des arguments. La **redéfinition** (*overriding*) est résolue à l'**exécution** (liaison dynamique), d'après
le type **réel** de l'objet. Autour : `@Override` fait vérifier la redéfinition par le compilateur, le type de retour
peut être covariant, et une méthode `static` est **masquée** et non redéfinie.

**Exemple :**

```java
class Printer {
    void print(Object o) { System.out.println("Object"); }
    void print(String s) { System.out.println("String"); }           // surcharge : autre signature
    static String kind() { return "Printer"; }
    Number value() { return 1; }
}
class ColorPrinter extends Printer {
    @Override void print(String s) { System.out.println("Color"); }  // redéfinition
    static String kind() { return "ColorPrinter"; }                  // masquage, pas redéfinition
    @Override Integer value() { return 2; }                          // type de retour covariant
}

Printer p = new ColorPrinter();
Object o = "hi";
p.print(o);     // "Object" : la surcharge est choisie à la compilation, sur le type statique de o
p.print("hi");  // "Color"  : la redéfinition est choisie à l'exécution, sur le type réel de p
p.kind();       // "Printer" : une méthode static dépend du type déclaré
```

#### Q9. Composition ou héritage : lequel choisir ? {#composition-vs-inheritance}
**Réponse :** « Favor composition over inheritance ». L'héritage exprime une relation « est un » et couple la sous-classe
à l'implémentation de son parent ; la composition exprime « a un » et n'expose que ce qui a du sens. Contre-exemple du JDK :
`Stack` hérite de `Vector` et en expose toutes les méthodes. Voir aussi
[Préférez la composition à l'héritage](../best-practices/java.md) pour l'exemple `HashSet`.

**Exemple :**

```java
// Contre-exemple du JDK : Stack hérite de Vector et en expose toutes les méthodes
Stack<Integer> s = new Stack<>();
s.push(1);
s.add(0, 99);   // insère au fond de la pile : l'invariant LIFO est cassé

// Composition : on n'expose que ce qui a du sens
final class LifoStack<E> {
    private final Deque<E> items = new ArrayDeque<>();
    void push(E e) { items.push(e); }
    E pop() { return items.pop(); }
    boolean isEmpty() { return items.isEmpty(); }
}
```

#### Q10. Couplage, cohésion et loi de Déméter : que faut-il savoir dire ? {#coupling-cohesion-law-of-demeter}
**Réponse :** On vise un **couplage faible** (peu de dépendances entre classes) et une **cohésion forte** (une classe
regroupe ce qui change ensemble). La **loi de Déméter** (« ne parle qu'à tes amis proches ») en est la règle pratique :
on ne traverse pas la structure interne d'un objet, on demande à celui qui détient l'information.

**Exemple :**

```java
// Couplage fort : l'appelant dépend de toute la structure interne
String city = order.getCustomer().getAddress().getCity();

// Mieux : on demande à l'objet qui détient l'information
String city = order.shippingCity();
```

Cohésion forte : `Order` porte les règles qui portent sur ses propres données (total, statut), au lieu de les laisser dans
un `OrderService`.

### Exceptions : les bases

#### Q11. Décrivez la hiérarchie des exceptions {#exception-hierarchy-error-vs-exception}
**Réponse :** Tout part de `Throwable`, qui a deux branches. `Error` : problèmes graves de la JVM, qu'on n'attrape pas.
`Exception` : problèmes que l'application peut traiter. Parmi les `Exception`, `RuntimeException` et ses sous-classes sont
**unchecked** (le compilateur n'impose rien) ; toutes les autres sont **checked** (il faut les attraper ou les déclarer
avec `throws`). Techniquement on peut attraper une `Error` (`catch (Throwable t)`), mais elle signale un état de la JVM dont
on ne peut pas se remettre de façon fiable (`OutOfMemoryError`, `StackOverflowError`). Seule exception tolérée : un
gestionnaire de dernier niveau qui journalise puis laisse mourir le thread ou le processus. En production :
`-XX:+HeapDumpOnOutOfMemoryError` et redémarrage par l'orchestrateur.

```text
Throwable
├── Error                                   unchecked : ne pas attraper
│   ├── VirtualMachineError
│   │   ├── OutOfMemoryError
│   │   └── StackOverflowError
│   ├── LinkageError
│   │   ├── NoClassDefFoundError
│   │   └── ExceptionInInitializerError
│   └── AssertionError
└── Exception                               checked
    ├── IOException
    │   ├── FileNotFoundException
    │   └── FileSystemException → NoSuchFileException
    ├── SQLException
    ├── InterruptedException
    ├── ReflectiveOperationException → ClassNotFoundException
    └── RuntimeException                    unchecked
        ├── NullPointerException
        ├── IllegalArgumentException → NumberFormatException
        ├── IllegalStateException
        ├── ArithmeticException
        ├── ClassCastException
        ├── IndexOutOfBoundsException → ArrayIndexOutOfBoundsException
        ├── UnsupportedOperationException
        ├── ConcurrentModificationException
        └── (Spring) DataAccessException, (JPA) PersistenceException
```

**À dire :**
- **Checked** : échec prévisible et récupérable, hors du contrôle du programme (fichier absent, réseau). Le compilateur
  force l'appelant à décider.
- **Unchecked** : bug ou contrat violé (`null`, argument invalide). Le corriger plutôt que l'attraper.
- Dans une application Spring, les erreurs métier sont en général des `RuntimeException` : elles traversent les couches et
  déclenchent le rollback de `@Transactional` (qui, par défaut, **ne fait pas** de rollback sur une checked, sauf avec
  `@Transactional(rollbackFor = Exception.class)`).

**Exemple :**

```java
// Exception métier : unchecked, avec le contexte utile au diagnostic
class InsufficientFundsException extends RuntimeException {
    InsufficientFundsException(String accountId, BigDecimal requested) {
        super("Solde insuffisant sur " + accountId + " pour " + requested);
    }
}

// Envelopper sans perdre la cause
try {
    return Files.readString(path);
} catch (IOException e) {
    throw new UncheckedIOException("Lecture impossible : " + path, e);   // la cause est conservée
}
```

**Pièges :**
- `ClassNotFoundException` (checked, chargement dynamique par nom) vs `NoClassDefFoundError` (`Error`, classe présente à la
  compilation mais absente ou cassée à l'exécution).
- Ne jamais avaler une exception (`catch (Exception e) {}`) ni perdre la cause (`throw new X(e.getMessage())` au lieu de
  `new X(msg, e)`).
- `catch (InterruptedException e)` : restaurer le statut avec `Thread.currentThread().interrupt()`.

Voir [Java Q35, checked vs unchecked](java-core-jvm.md#checked-unchecked-exceptions-design-trade).

#### Q12. L'ordre des blocs `catch` a-t-il de l'importance ? {#catch-block-order-multi-catch}
**Réponse :** Oui. Les blocs `catch` sont testés **de haut en bas** et seul le **premier** qui correspond s'exécute. Il faut
donc aller du **plus spécifique au plus général**. Si un `catch` parent précède un `catch` enfant, l'enfant est
inatteignable : c'est une **erreur de compilation**, pas un simple avertissement. Entre types sans lien d'héritage, l'ordre
n'a aucune importance.

**Exemple :**

```java
try {
    String content = Files.readString(path);
    int qty = Integer.parseInt(content.trim());
} catch (NoSuchFileException e) {              // le plus spécifique d'abord
    log.warn("Fichier absent : {}", path);
} catch (IOException e) {                      // puis son parent
    throw new UncheckedIOException(e);
} catch (NumberFormatException e) {            // sans lien avec IOException : position libre
    throw new IllegalArgumentException("Quantité invalide dans " + path, e);
}

// Inversé :
// catch (IOException e) { ... }
// catch (NoSuchFileException e) { ... }       // erreur : exception NoSuchFileException has already been caught
```

**Multi-catch (Java 7).** Factorise le traitement de types **sans lien d'héritage**.

```java
catch (NoSuchFileException | NumberFormatException e) { ... }   // OK
// catch (NoSuchFileException | IOException e)                   // erreur : types liés par héritage
// Dans un multi-catch, e est implicitement final
```

**Pièges :**
- `catch (Exception e)` en premier rend tous les suivants inatteignables (erreur de compilation).
- Le `finally` s'exécute après le `catch` choisi, que le `catch` relance ou non.
- Le compilateur refuse aussi un `catch` d'une exception checked que le bloc `try` ne peut pas lever (`catch (IOException e)`
  autour d'un code sans I/O).

#### Q13. `final`, `finally`, `finalize` : quelles différences, et que renvoie une méthode avec un `return` dans `try` et `finally` ? {#final-finally-finalize-return-in-finally}
**Réponse :** `final` est un **mot-clé** : variable affectée une seule fois, méthode non redéfinissable, classe non
héritable. `finally` est un **bloc** toujours exécuté après `try`/`catch`, pour libérer une ressource (remplacé le plus
souvent par try-with-resources). `finalize()` est une **méthode** d'`Object` appelée par le GC avant la destruction, sans
garantie de moment ni d'exécution ; dépréciée pour suppression depuis Java 18 (JEP 421), on utilise try-with-resources ou
`java.lang.ref.Cleaner`. Le `finally` ne s'exécute pas si la JVM s'arrête : `System.exit()`, crash, `kill -9`.

**Exemple :**

```java
static int a() {
    try { return 1; }
    finally { System.out.println("finally"); }   // affiché AVANT que la méthode ne rende 1
}

static int b() {
    int x = 1;
    try { return x; }                          // la valeur 1 est déjà évaluée et mise de côté
    finally { x = 2; }                         // sans effet sur la valeur renvoyée : b() renvoie 1
}

static int c() {
    try { throw new IllegalStateException(); }
    finally { return 3; }                      // renvoie 3 et AVALE l'exception : à proscrire
}
```

### Collections & génériques

#### Q14. `ArrayList` vs `LinkedList`, `HashMap` vs `TreeMap` vs `LinkedHashMap` — comment choisir une collection ? {#arraylist-linkedlist-hashmap-treemap-linkedhashmap}
**Réponse :** Par défaut **`ArrayList`** : mémoire contiguë, accès par index en O(1) et itération rapide grâce aux
caches CPU. `LinkedList` ne gagne qu'en théorie (insertion en O(1) sur un nœud connu) ; en pratique atteindre le nœud
coûte O(n) et chaque nœud est un objet séparé, donc elle est presque toujours plus lente. Pour une file ou une pile,
utilisez **`ArrayDeque`**. Pour les maps : **`HashMap`** pour une recherche en O(1) sans ordre ; **`LinkedHashMap`**
pour garder l'ordre d'insertion (ou d'accès, pour un cache LRU) ; **`TreeMap`** pour des clés triées et des requêtes
par plage (`headMap`, `ceilingKey`) en O(log n). Même logique pour `HashSet`, `LinkedHashSet`, `TreeSet`. En
concurrence, utilisez `ConcurrentHashMap`, pas `Collections.synchronizedMap`. Préférez `List.of`/`Map.of` pour des
données fixes et immuables.

**Exemple :**

```java
Deque<Task> stack = new ArrayDeque<>();                    // ni Stack, ni LinkedList
NavigableMap<LocalDate, Rate> rates = new TreeMap<>();
Rate applicable = rates.floorEntry(invoiceDate).getValue(); // dernier taux à la date ou avant
```

**Pour aller plus loin sur le choix :** `HashSet` est une `HashMap` dont les éléments sont les clés (valeur factice
partagée). `Hashtable` est l'ancêtre synchronisé (chaque méthode verrouille toute la table) et refuse les `null` : à
remplacer par `ConcurrentHashMap`.

| Collection | Accès / recherche | Ajout | Ordre | Quand l'utiliser |
|---|---|---|---|---|
| `ArrayList` | `get(i)` O(1), `contains` O(n) | fin O(1) amorti, milieu O(n) | insertion | le choix par défaut pour une liste |
| `LinkedList` | `get(i)` O(n) | extrémités O(1) | insertion | presque jamais : `ArrayDeque` fait mieux |
| `ArrayDeque` | extrémités O(1) | O(1) | insertion | pile ou file |
| `HashMap` / `HashSet` | O(1) en moyenne | O(1) | aucun | recherche par clé |
| `LinkedHashMap` | O(1) | O(1) | insertion (ou accès : cache LRU) | ordre prévisible |
| `TreeMap` / `TreeSet` | O(log n) | O(log n) | trié | plages : `floorKey`, `subMap`, `headMap` |
| `PriorityQueue` | `peek` O(1) | `offer`/`poll` O(log n) | tas | top K, planification |

Exemple de raisonnement : « Je dois trouver le dernier cours connu à une date donnée » → `TreeMap<LocalDate, BigDecimal>`
puis `floorEntry(date)` en O(log n).

#### Q15. List ou Set : comment choisir ? {#list-vs-set-choose}
**Réponse :** Une `List` est une séquence **ordonnée, indexée, qui accepte les doublons**. Un `Set` est un ensemble **sans
doublons**, sans index, dont l'ordre dépend de l'implémentation. On choisit `Set` quand l'unicité compte ou quand on teste
souvent l'appartenance (`contains` en O(1) pour un `HashSet`, contre O(n) pour une `ArrayList`).

| | `ArrayList` | `HashSet` | `LinkedHashSet` | `TreeSet` |
|---|---|---|---|---|
| Doublons | oui | non | non | non |
| Ordre | insertion | aucun | insertion | trié |
| `get(i)` | O(1) | n/a | n/a | n/a |
| `contains` | O(n) | O(1) moyen | O(1) moyen | O(log n) |
| `null` | oui | un seul | un seul | non (NPE) |
| Égalité basée sur | `equals` | `hashCode` + `equals` | `hashCode` + `equals` | `compareTo` / `Comparator` |

**Exemple :**

```java
List<String> isins = List.of("FR001", "US002", "FR001");
Set<String> unique = new HashSet<>(isins);              // [US002, FR001] : ordre imprévisible
Set<String> ordered = new LinkedHashSet<>(isins);       // [FR001, US002] : dédoublonné, ordre conservé
List<String> back = new ArrayList<>(ordered);           // retour à une List si on a besoin d'un index
List<String> viaStream = isins.stream().distinct().toList();   // même résultat en stream

Set<String> blocked = Set.of("RU123", "IR456");
boolean ok = !blocked.contains(isin);                   // O(1) : liste noire, contrôle d'appartenance
```

**Pièges :**
- Un `HashSet` est en réalité une `HashMap` dont les éléments sont les clés : sans `equals`/`hashCode` corrects, les
  doublons passent (voir [Java Q3](java-core-jvm.md#equals-hashcode-contract-breaks-override)).
- Modifier un champ utilisé par `hashCode` après l'insertion rend l'élément introuvable.
- `TreeSet` utilise `compareTo` et non `equals` : `new BigDecimal("2.0")` et `"2.00"` y sont un seul élément, mais deux dans
  un `HashSet`.
- `List.remove(int index)` vs `List.remove(Object o)` : sur une `List<Integer>`, `remove(1)` supprime l'index 1, pas la
  valeur 1.

**Usage réel :** avec JPA, une association `@OneToMany` en `Set` évite la `MultipleBagFetchException`, mais exige un
`equals`/`hashCode` stable sur l'entité.

#### Q16. Quelles sont les façons d'itérer sur une collection, et laquelle choisir ? {#ways-to-iterate-collection}
**Réponse :** Il y en a six principales : la boucle indexée, la boucle for-each, l'`Iterator` explicite, `ListIterator`,
`forEach` avec une lambda, et les streams. Pour une `Map`, on itère sur `entrySet()`. **Par défaut : la boucle for-each**,
la plus lisible et sûre pour toutes les collections. Les autres répondent à un besoin précis.

**Exemple :**

```java
List<Trade> trades = repo.findAll();

// 1. Boucle indexée : seulement si on a besoin de l'index, et seulement sur une liste à accès direct
for (int i = 0; i < trades.size(); i++) {
    System.out.println(i + " : " + trades.get(i));
}

// 2. For-each : le choix par défaut (compilé en Iterator pour une collection)
for (Trade t : trades) {
    process(t);
}

// 3. Iterator explicite : pour supprimer pendant le parcours
for (Iterator<Trade> it = trades.iterator(); it.hasNext(); ) {
    if (it.next().isCancelled()) it.remove();
}
trades.removeIf(Trade::isCancelled);   // équivalent moderne, plus court

// 4. ListIterator : parcours dans les deux sens, remplacement ou insertion en place
for (ListIterator<String> it = codes.listIterator(); it.hasNext(); ) {
    it.set(it.next().toUpperCase());
}
codes.replaceAll(String::toUpperCase); // équivalent moderne

// 5. forEach + lambda : une action simple par élément
trades.forEach(this::publish);

// 6. Stream : pour transformer, filtrer, agréger
List<String> fxIds = trades.stream()
        .filter(t -> t.desk().equals("FX"))
        .map(Trade::id)
        .toList();
```

**Pour une `Map` :**

```java
// Bien : une seule recherche par entrée
for (Map.Entry<String, BigDecimal> e : balances.entrySet()) {
    System.out.println(e.getKey() + " = " + e.getValue());
}
balances.forEach((account, balance) -> System.out.println(account + " = " + balance));

// Moins bien : keySet + get = une recherche supplémentaire par clé
for (String account : balances.keySet()) {
    System.out.println(account + " = " + balances.get(account));
}
```

**Quelle option choisir ?**

| Besoin | Meilleure option |
|---|---|
| Parcourir simplement | for-each |
| Besoin de l'index | boucle indexée (sur `ArrayList` ou tableau uniquement) |
| Supprimer pendant le parcours | `removeIf`, ou `Iterator.remove()` |
| Modifier chaque élément en place | `replaceAll`, ou `ListIterator.set()` |
| Transformer, filtrer, agréger | stream |
| Clés et valeurs d'une `Map` | `entrySet()` ou `Map.forEach` |
| Sortie anticipée (`break`, `return`) ou exception checked | for-each (impossible dans une lambda `forEach`) |

**Pièges :**
- `list.remove(x)` dans un for-each → `ConcurrentModificationException` (voir [Java Q38](java-core-jvm.md#causes-concurrentmodificationexception-correct-fix)).
- Boucle indexée sur une `LinkedList` : `get(i)` est en O(n), donc le parcours devient O(n²).
- `forEach` avec une lambda n'accepte ni `break` ni `continue` (`return` = `continue`), ni variable locale modifiée.
- Les performances des boucles sont équivalentes sur une `ArrayList` : on choisit pour la lisibilité, pas pour la vitesse.
- Les collections concurrentes (`CopyOnWriteArrayList`, `ConcurrentHashMap`) ont des itérateurs *weakly consistent* : pas de
  `ConcurrentModificationException`, mais pas forcément les dernières modifications.

#### Q17. `Comparable` vs `Comparator`, et que signifie PECS pour les génériques ? {#comparable-comparator-pecs-generics}
**Réponse :** `Comparable` définit l'**ordre naturel** d'un type dans la classe elle-même (`compareTo`), et il n'y en a
qu'un. `Comparator` définit un **ordre externe**, on peut donc en avoir plusieurs
(`Comparator.comparing(Order::total).reversed().thenComparing(Order::id)`). Gardez `compareTo` cohérent avec `equals`,
sinon les sets et maps triés se comportent bizarrement (`BigDecimal("1.0")` et `BigDecimal("1.00")` sont égaux selon
`compareTo` mais pas selon `equals`). **PECS** (« Producer Extends, Consumer Super ») indique quel joker utiliser : un
paramètre dans lequel on ne fait que **lire** est un producteur, donc `? extends T` ; un paramètre dans lequel on ne
fait qu'**écrire** est un consommateur, donc `? super T`. C'est pourquoi `Collections.sort(List<T>, Comparator<? super T>)`
accepte un `Comparator<Object>` pour une `List<String>`.

**Exemple :**

```java
static double sum(Collection<? extends Number> nums) {        // producteur : on lit des Number
    return nums.stream().mapToDouble(Number::doubleValue).sum();
}
static void fill(List<? super Integer> out) { out.add(42); }  // consommateur : on écrit des Integer
sum(List.of(1, 2.5, 3L));
fill(new ArrayList<Number>());
```

### Versions, JDK & build

#### Q18. Quelles sont les versions LTS de Java et leurs nouveautés phares, et quelle différence entre JDK, JRE et JVM ? {#java-lts-versions-features-jdk-jre-jvm}
**Réponse :** **LTS** : 8 (lambdas, streams, `Optional`, `java.time`, méthodes `default`) ; 11 (`HttpClient`, `var` dans les lambdas, `String.isBlank`/`strip`/`lines`, lancement direct d'un fichier `.java`, retrait des modules Java EE) ; 17 (records, classes `sealed`, pattern matching pour `instanceof`, text blocks, expressions `switch`) ; 21 (virtual threads, pattern matching dans `switch`, record patterns, sequenced collections, ZGC générationnel) ; 25 (méthodes `main` d'instance et fichiers source compacts, `import module`, instructions avant `super(...)` dans les constructeurs, scoped values, en-têtes d'objets compacts). **Cadence** : une version tous les 6 mois (mars et septembre), une LTS tous les 2 ans depuis Java 17 ; en entreprise on monte de LTS en LTS. **JVM** : exécute le bytecode ; **JRE** = JVM + bibliothèques standard ; **JDK** = JRE + outils (`javac`, `jar`, `jcmd`, `jfr`…). Depuis Java 11, il n'y a plus de JRE séparé chez Oracle : on construit un runtime minimal avec `jlink`. **OpenJDK vs Oracle JDK** : même code source ; OpenJDK est l'implémentation de référence, Temurin (Eclipse Adoptium), Corretto (Amazon) ou Zulu (Azul) en sont des builds gratuits avec support long, tandis que l'Oracle JDK impose une licence payante en production selon les versions. **JCP et JEP** : le JCP fait évoluer les spécifications ; une JEP décrit une évolution précise d'OpenJDK (JEP 444 pour les virtual threads).

**Exemple :**

```java
// Java 8 : lambdas, streams, Optional, java.time
List<String> desks = trades.stream()
        .filter(t -> t.notional().signum() > 0)
        .map(Trade::desk).distinct().collect(Collectors.toList());
LocalDate valueDate = LocalDate.of(2026, 10, 29).plusDays(2);   // immuable et thread-safe, contrairement à Date

// Java 11 : HttpClient, nouvelles méthodes de String
HttpClient http = HttpClient.newHttpClient();
HttpResponse<String> resp = http.send(
        HttpRequest.newBuilder(URI.create("https://api.example.com/rates")).build(),
        HttpResponse.BodyHandlers.ofString());
"  ".isBlank();                        // true ; et "a\nb".lines(), " x ".strip()
// $ java Hello.java                   → lance un fichier source sans passer par javac

// Java 17 : records, sealed, pattern matching pour instanceof, switch expression
if (obj instanceof Trade t && t.notional().signum() > 0) { /* t déjà typé */ }
String label = switch (day) { case SATURDAY, SUNDAY -> "week-end"; default -> "semaine"; };

// Java 21 : virtual threads, pattern matching dans switch, sequenced collections
Thread.startVirtualThread(() -> System.out.println("hello"));
List<String> l = List.of("a", "b", "c");
l.getFirst(); l.getLast(); l.reversed();   // SequencedCollection : enfin une API commune

// Java 25 : fichier source compact et main d'instance (le fichier entier)
void main() {
    IO.println("Bonjour");                 // ni classe, ni static, ni String[] args
}
```

Runtime minimal avec `jlink` :

```bash
jdeps --print-module-deps app.jar                      # → java.base,java.net.http,java.sql
jlink --add-modules java.base,java.net.http,java.sql \
      --strip-debug --no-header-files --no-man-pages --output runtime
./runtime/bin/java -jar app.jar                        # une image de quelques dizaines de Mo au lieu d'un JDK complet
```


**Avantages d'une LTS :**
- **Sécurité** : patchs trimestriels pendant des années (builds gratuits Temurin, Corretto, Zulu).
- **Écosystème** : frameworks, serveurs d'applications et outils sont certifiés sur les LTS (Spring Boot, Hibernate,
  agents APM).
- **Moins de migrations** : une tous les 2 ans au lieu de tous les 6 mois, ce qui compte quand chaque montée de version
  passe par une homologation.
- **Stabilité** : une LTS regroupe les fonctionnalités finalisées des versions précédentes ; les fonctionnalités en
  *preview* restent désactivées par défaut.

**Ce qu'apporte Java 25 (septembre 2025) par rapport à 21.** Fonctionnalités finalisées de 22 à 25 :

| Fonctionnalité | JEP | Intérêt |
|---|---|---|
| Variables anonymes `_` | 456 (22) | ignorer un paramètre ou une exception inutilisés |
| API Foreign Function & Memory | 454 (22) | appeler du natif sans JNI |
| Stream gatherers | 485 (24) | opérations intermédiaires sur mesure (fenêtres, regroupements) |
| Virtual threads sans pinning sur `synchronized` | 491 (24) | plus besoin de remplacer `synchronized` par `ReentrantLock` |
| Scoped values | 506 (25) | remplace `ThreadLocal`, adapté aux virtual threads |
| `import module` | 511 (25) | importer tous les packages d'un module en une ligne |
| Fichiers source compacts, `main` d'instance | 512 (25) | scripts et apprentissage sans boilerplate |
| Instructions avant `super(...)` | 513 (25) | valider les arguments avant d'appeler le constructeur parent |
| En-têtes d'objets compacts | 519 (25) | en-tête de 12 à 8 octets : moins de heap, meilleure localité |
| Cache AOT (ergonomie, profilage) | 514, 515 (25) | démarrage et montée en charge plus rapides |
| Shenandoah générationnel | 521 (25) | GC basse latence plus efficace |

**Exemple Java 22–25 :**

```java
// Variables anonymes (22)
try { Integer.parseInt(s); } catch (NumberFormatException _) { return false; }
switch (payment) {
    case Card _, Cash _ -> handleSimple();
    case Transfer t -> handleTransfer(t);
}

// Stream gatherers (24)
Stream.of(1, 2, 3, 4, 5).gather(Gatherers.windowFixed(2)).toList();   // [[1, 2], [3, 4], [5]]

// Instructions avant super(...) (25)
class Trade extends Entity {
    Trade(String id, Instant createdAt) {
        if (id.isBlank()) throw new IllegalArgumentException("id vide");   // interdit avant Java 25
        super(createdAt);
    }
}

// Scoped values (25) : un contexte immuable, visible dans toute la pile d'appels, libéré à la sortie
static final ScopedValue<String> USER = ScopedValue.newInstance();
ScopedValue.where(USER, "u123").run(() -> paymentService.handle());   // USER.get() dans handle()

// import module (25)
import module java.base;              // java.util, java.io, java.time... en une ligne
```

```bash
# En-têtes compacts : à activer explicitement en 25
java -XX:+UseCompactObjectHeaders -jar app.jar
```

**Ce qui reste en preview dans 25** (à ne pas présenter comme finalisé) : structured concurrency, patterns sur les types
primitifs, *stable values*.

**À dire en conclusion :** « Passer de 21 à 25, c'est un gain gratuit en mémoire et en démarrage, des virtual threads enfin
utilisables avec du code `synchronized` existant, et plusieurs années de support en plus. »

#### Q19. Maven ou Gradle : quelles différences, et à quoi ressemble la même dépendance ? {#maven-vs-gradle}
**Réponse :** Maven est déclaratif (XML, cycle de vie fixe, conventions fortes) ; Gradle est programmable (DSL Kotlin ou Groovy), incrémental et doté d'un cache de build, donc plus rapide sur les gros projets mais plus libre. Maven suit un cycle de vie fixe (`validate → compile → test → package → verify → install → deploy`), et `mvn verify` exécute tout jusqu'à `verify`. Gradle exécute un graphe de tâches (`./gradlew build`), ne relance que ce qui a changé, et distingue `api` (dépendance exposée aux consommateurs) de `implementation` (dépendance cachée).

**Exemple :**

```xml
<!-- pom.xml -->
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>junit-jupiter</artifactId>
  <scope>test</scope>
</dependency>
```

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    testImplementation("org.junit.jupiter:junit-jupiter")
}
```

**Comparator en pratique :** pour trier sur plusieurs critères, on chaîne les comparateurs ; un piège classique est la
soustraction.

```java
record Trade(String desk, BigDecimal notional, Instant time) {}

trades.sort(Comparator.comparing(Trade::desk)
        .thenComparing(Trade::notional, Comparator.reverseOrder())
        .thenComparing(Trade::time));
// Comparable : l'ordre naturel, écrit dans la classe (compareTo) ; Comparator : des ordres externes, autant qu'on veut

// Piège : (a, b) -> a.qty - b.qty déborde avec de grands entiers ou des négatifs → Integer.compare(a.qty, b.qty)

// PECS : Producer Extends, Consumer Super
static <T> void copy(List<? super T> dest, List<? extends T> src) {
    for (T t : src) dest.add(t);       // src produit des T (extends), dest consomme des T (super)
}
List<Number> numbers = new ArrayList<>();
copy(numbers, List.of(1, 2, 3));       // T = Integer, et une List<Number> accepte des Integer
// List<? extends Number> : on peut y lire des Number, mais pas y ajouter (sauf null)
```

### Java moderne : lambdas & streams

#### Q20. Interface fonctionnelle ou lambda : quelle différence ? {#functional-interface-vs-lambda}
**Réponse :** Ce ne sont pas deux choses du même niveau. Une **interface fonctionnelle** est un **type** : une interface
avec **une seule méthode abstraite**. Une **lambda** est une **expression** qui fournit une **implémentation** de cette
méthode. Une lambda n'existe jamais seule : elle a toujours pour type cible une interface fonctionnelle.

**Exemple :**

```java
@FunctionalInterface                  // facultatif, mais le compilateur vérifie qu'il n'y a qu'une méthode abstraite
interface FeeRule {
    BigDecimal apply(BigDecimal amount);                         // la méthode abstraite unique

    default FeeRule capped(BigDecimal max) {                     // autorisé : méthode default
        return amount -> apply(amount).min(max);
    }

    static FeeRule rate(String rate) {                           // autorisé : méthode static
        return amount -> amount.multiply(new BigDecimal(rate));
    }

    boolean equals(Object o);                                    // autorisé : les méthodes d'Object ne comptent pas
}

// Trois façons d'implémenter la même interface
FeeRule anonymous = new FeeRule() {                              // avant Java 8 : classe anonyme
    public BigDecimal apply(BigDecimal amount) { return BigDecimal.ONE; }
};
FeeRule lambda = amount -> amount.multiply(new BigDecimal("0.015"));
FeeRule methodRef = BigDecimal::negate;                          // référence de méthode : lambda abrégée

FeeRule card = FeeRule.rate("0.015").capped(new BigDecimal("50"));
card.apply(new BigDecimal("10000"));                             // 50 : plafonné
```

**Les interfaces fonctionnelles du JDK** (`java.util.function`) : `Function<T, R>` (`T -> R`), `Predicate<T>` (`T ->
boolean`), `Supplier<T>` (`() -> T`), `Consumer<T>` (`T -> void`), `UnaryOperator<T>`, `BinaryOperator<T>`, leurs variantes
`Bi…` et primitives (`IntPredicate`, sans boxing). Et les historiques : `Runnable`, `Callable`, `Comparator`.

**Lambda vs classe anonyme :**

| | Lambda | Classe anonyme |
|---|---|---|
| Cible | interface fonctionnelle uniquement | interface ou classe, plusieurs méthodes possibles |
| `this` | l'instance englobante | l'instance anonyme |
| État | aucun champ propre | peut avoir des champs |
| Compilation | `invokedynamic`, pas de fichier `.class` | un fichier `Outer$1.class` |

**Pièges :**
- Variables capturées : elles doivent être *effectively final*. `int count = 0; list.forEach(x -> count++);` ne compile pas →
  `AtomicInteger`, ou mieux, `list.size()` / un stream.
- Une lambda ne peut pas lever d'exception checked si la méthode de l'interface ne la déclare pas (`Function.apply` ne
  déclare rien).
- `var f = x -> x * 2;` ne compile pas : sans type cible, le compilateur ne sait pas quelle interface implémenter.
- `Comparator` déclare `equals` en abstrait et reste fonctionnelle : les méthodes publiques d'`Object` ne comptent pas.

#### Q21. L'annotation `@FunctionalInterface` est-elle obligatoire ? {#functional-interface-annotation-optional}
**Réponse :** Non. Toute interface qui a **exactement une méthode abstraite** est fonctionnelle et accepte une lambda,
annotée ou pas. `@FunctionalInterface` est une **bonne pratique** : elle documente l'intention (« cette interface est faite
pour des lambdas ») et demande au **compilateur de vérifier** la règle. Si quelqu'un ajoute plus tard une deuxième méthode
abstraite, l'erreur tombe sur l'interface elle-même, au lieu de casser toutes les lambdas qui l'utilisent. C'est le même
principe qu'`@Override` : facultatif, mais le compilateur transforme une erreur silencieuse en erreur explicite. Le JDK la
met sur `Function`, `Predicate` ou `Runnable`.

**Exemple :**

```java
// Sans annotation : fonctionne quand même
interface Validator {
    boolean validate(Trade t);
}
Validator positive = t -> t.notional().signum() > 0;      // compile

// Six mois plus tard, quelqu'un ajoute une méthode abstraite :
interface Validator {
    boolean validate(Trade t);
    String errorMessage();                                // l'interface compile toujours...
}
// ... mais chaque lambda, partout dans le code (et chez les équipes qui utilisent la librairie), casse :
// error: incompatible types: Validator is not a functional interface

// Avec annotation : l'erreur est immédiate, au bon endroit
@FunctionalInterface
interface Validator {
    boolean validate(Trade t);
    String errorMessage();
    // error: Unexpected @FunctionalInterface annotation
    //   Validator is not a functional interface: multiple non-overriding abstract methods found
}

// La bonne évolution : une méthode default ne casse rien
@FunctionalInterface
interface Validator {
    boolean validate(Trade t);
    default String errorMessage() { return "invalid trade"; }
}
```

**Pièges :**
- Ne comptent pas comme méthodes abstraites : les méthodes `default`, `static`, et les méthodes publiques d'`Object`
  redéclarées (`equals`, `toString`).
- L'annotation sur une classe, une classe abstraite ou une enum est une erreur de compilation : seules les interfaces
  peuvent être fonctionnelles.
- Une interface qui étend une interface fonctionnelle reste fonctionnelle tant qu'elle n'ajoute pas de méthode abstraite.
- L'annotation est `@Documented` : elle apparaît dans la Javadoc, ce qui informe les utilisateurs de l'API.

#### Q22. `map` ou `flatMap` ? Et que sont les méthodes `default`, `var` et les text blocks ? {#default-methods-var-text-blocks}
**Réponse :** `map` transforme chaque élément en **un** résultat ; `flatMap` transforme chaque élément en un **stream** (ou
un `Optional`) puis **aplatit** le tout d'un niveau. Même logique pour `Optional` : `opt.flatMap(this::findOwner)` quand
`findOwner` renvoie déjà un `Optional`. Les méthodes `default` permettent de faire évoluer une interface sans casser ses
implémentations (`List.sort`, `Collection.stream` en Java 8). `var` est une inférence de type locale. Les text blocks
(`"""`) écrivent des chaînes multi-lignes.

**Exemple :**

```java
List<List<String>> byDesk = List.of(List.of("T1", "T2"), List.of("T3"));
byDesk.stream().map(List::stream);                        // Stream<Stream<String>> : un niveau de trop
byDesk.stream().flatMap(List::stream).toList();           // [T1, T2, T3] : aplati

// default : faire évoluer une interface sans casser ses implémentations
interface Priced {
    BigDecimal price();
    default BigDecimal priceWithVat() { return price().multiply(new BigDecimal("1.20")); }
}

var trades = new HashMap<String, List<Trade>>();   // inférence locale ; interdit en champ, en paramètre, avec null
var list = new ArrayList<>();                      // piège : ArrayList<Object>

String json = """
        {"id": "T1", "amount": 100.50}
        """;                                         // indentation commune retirée, saut de ligne final inclus
```

### Concurrence : les bases

#### Q23. Multithreading : comment créer et coordonner des threads en Java ? {#create-coordinate-threads-basics}
**Réponse :** Un **processus** a sa propre mémoire ; ses **threads** partagent le heap et ont chacun leur stack. Le
multithreading sert à exécuter plusieurs tâches en parallèle (CPU) ou à ne pas bloquer pendant les attentes (I/O). En
pratique, on ne crée pas de threads à la main : on soumet des **tâches** à un **pool** (`ExecutorService`), et on protège
l'état partagé.

**Les façons de lancer du travail concurrent, de la plus ancienne à la plus moderne :**

```java
// 1. Hériter de Thread : à éviter (on gaspille l'héritage, on mélange tâche et mécanisme)
class Worker extends Thread { public void run() { /* ... */ } }
new Worker().start();

// 2. Runnable : la tâche sans résultat, séparée du thread
Thread t = new Thread(() -> System.out.println("hello"));
t.start();                             // start() crée un nouveau thread ; run() s'exécuterait dans le thread courant
t.join();                              // attendre la fin

// 3. Callable + Future : une tâche qui renvoie un résultat et peut lever une exception checked
try (ExecutorService pool = Executors.newFixedThreadPool(4)) {
    Future<BigDecimal> price = pool.submit(() -> pricer.price("FR0000131104"));
    BigDecimal p = price.get(2, TimeUnit.SECONDS);   // bloquant, avec timeout
}

// 4. CompletableFuture : composer des tâches asynchrones sans bloquer
CompletableFuture.supplyAsync(() -> clientApi.get(id), pool)
        .thenApply(Client::name)
        .exceptionally(ex -> "inconnu");

// 5. Virtual threads (Java 21) : un thread léger par tâche, idéal pour l'I/O bloquante
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    ids.forEach(id -> executor.submit(() -> clientApi.get(id)));
}
```

**Cycle de vie d'un thread** (`Thread.State`) : `NEW` → `RUNNABLE` → (`BLOCKED` en attente d'un moniteur, `WAITING` /
`TIMED_WAITING` sur `join`, `wait`, `sleep`, `park`) → `TERMINATED`.

**Coordonner et protéger :**

| Besoin | Outil |
|---|---|
| Exclusion mutuelle | `synchronized`, `ReentrantLock` |
| Visibilité d'un drapeau | `volatile` |
| Compteur, référence atomique | `AtomicInteger`, `AtomicReference`, `LongAdder` |
| Map partagée | `ConcurrentHashMap` (`merge`, `computeIfAbsent`) |
| Producteur / consommateur | `BlockingQueue` (`ArrayBlockingQueue`) |
| Attendre N tâches | `CountDownLatch`, `invokeAll`, `CompletableFuture.allOf` |
| Limiter l'accès concurrent | `Semaphore` (ex. 10 appels simultanés à une API) |

**Pièges :**
- `run()` au lieu de `start()` : aucun nouveau thread.
- `sleep` garde les verrous ; `wait` relâche le moniteur (et s'appelle dans un `synchronized`, dans une boucle `while`).
- Oublier de fermer un `ExecutorService` : la JVM ne s'arrête pas (threads non démons).
- Une exception dans une tâche soumise par `submit` est capturée dans le `Future` : sans `get()`, elle passe inaperçue.
- Race condition (`count++`), deadlock (verrous pris dans un ordre différent) : voir [Java Q40](java-core-jvm.md#race-condition-deadlock-thread-starvation).

**Usage réel :** paralléliser des appels à plusieurs services (`CompletableFuture` + pool dédié), batchs CPU (pool de la
taille du nombre de cœurs), serveur web à forte concurrence I/O (virtual threads). Voir
[Java Q48, `ExecutorService`](java-core-jvm.md#using-executorservice-creating-raw-thread) et
[Java Q52, virtual threads](java-core-jvm.md#problem-virtual-threads-project-loom).

### Mémoire JVM : les bases

#### Q24. Heap ou stack : qu'est-ce qui vit où ? {#heap-vs-stack}
**Réponse :** La **stack** est propre à chaque thread : elle contient une *frame* par appel de méthode, avec les variables
locales, les primitifs et les **références**. Elle est libérée automatiquement au retour de la méthode. Le **heap** est
partagé par tous les threads : il contient **tous les objets** (et les tableaux), et c'est le garbage collector qui le
libère.

| | Stack | Heap |
|---|---|---|
| Contenu | frames : variables locales, primitifs, références, adresse de retour | objets, tableaux, string pool (depuis Java 7) |
| Portée | un thread | toute la JVM |
| Durée de vie | celle de l'appel de méthode | jusqu'à ce que l'objet ne soit plus accessible |
| Libération | automatique, au dépilement | garbage collector |
| Taille | petite, `-Xss` (souvent 512 Ko à 1 Mo) | grande, `-Xms` / `-Xmx` |
| Vitesse | allocation quasi gratuite | allocation rapide (TLAB), mais coût du GC |
| Thread-safety | naturelle : rien n'est partagé | à gérer |
| Erreur si plein | `StackOverflowError` | `OutOfMemoryError: Java heap space` |

**Exemple :**

```java
void book(int qty) {                   // qty : primitif, dans la frame de book (stack)
    Trade t = new Trade("T1", qty);    // t : référence sur la stack ; l'objet Trade : sur le heap
    List<Trade> batch = List.of(t);    // une 2e référence vers le même objet du heap
    repo.save(t);                      // nouvelle frame empilée pour save, dépilée au retour
}                                      // frame de book dépilée : l'objet Trade devient éligible au GC
```

**Pièges :**
- « Les primitifs sont sur la stack » n'est vrai que pour les **variables locales**. Un champ `int` d'un objet vit dans
  l'objet, donc sur le heap.
- Java passe tout **par valeur** : pour un objet, c'est la référence qui est copiée. Réaffecter le paramètre ne change rien
  chez l'appelant ; modifier l'objet, si.
- Le JIT peut éviter une allocation sur le heap grâce à l'*escape analysis* (objet qui ne sort pas de la méthode).

**Usage réel :** diagnostiquer : `StackOverflowError` → récursion ; `OutOfMemoryError` → heap dump et Eclipse MAT. Dans un
conteneur, la mémoire totale = heap + metaspace + stacks des threads + mémoire native : d'où `-XX:MaxRAMPercentage=75`
plutôt que 100 %. Détail des zones : [R9](java-core-jvm.md#java-memory-management-different-jvm).

## 🟡 Pièges seniors

### Langage & types

#### Q25. Pourquoi `String` est-elle immuable, et qu'est-ce que le string pool ? {#string-immutable-string-pool}
**Réponse :** Une fois créé, le stockage interne des caractères d'une `String` n'est jamais modifié — chaque
méthode « modifiante » (`concat`, `substring`, `replace`) retourne une nouvelle `String`. Cela apporte la
thread safety sans synchronisation (partage sûr entre threads), permet d'utiliser une `String` sans risque comme
clé de `HashMap` (son hash peut être mis en cache, calculé une fois et stocké dans l'objet — voir la discussion
sur la performance à la Q18), et rend possible le **string pool** — les chaînes littérales (et les chaînes
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

**Compléments sur le pool :** `String d = "hel" + "lo";` est une constante calculée à la compilation, donc `a == d` est
`true`, alors que `String part = "hel"; a == part + "lo"` est `false` (concaténation à l'exécution, donc nouvel objet).
`new String("hello")` crée 1 ou 2 objets : celui du heap, plus le littéral `"hello"` dans le pool s'il n'y est pas encore.

#### Q26. Quel est le piège de `==` avec l'autoboxing sur `Integer` ? {#autoboxing-trap-integer}
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

#### Q27. Qu'est-ce que le type erasure, et qu'est-ce que cela casse réellement ? {#type-erasure-break}
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

#### Q28. Qu'apporte le compact canonical constructor d'un record que `@Data` de Lombok ne garantit pas structurellement ? {#record-compact-canonical-constructor-buy}
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

#### Q29. Comment le pattern matching pour `switch` se combine-t-il avec les sealed types, et pourquoi est-ce important pour l'exhaustivité ? {#pattern-matching-switch-combine-sealed}
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

#### Q30. Où `Optional` aide-t-il, et où son usage dégrade-t-il le code ? {#optional-help-using-make-code}
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

#### Q31. Quelles sont les façons courantes dont un pipeline `Stream` tourne mal, même lorsqu'il compile et « marche » dans un test ? {#common-ways-stream-pipeline-goes}
**Réponse :** Cinq cas récurrents. (1) **Laziness** : les opérations intermédiaires (`map`, `filter`,
`peek`) ne font rien tant qu'une opération terminale ne s'exécute pas, donc un pipeline sans opération terminale
ne fait silencieusement rien, et `peek` est une aide au debug, pas un endroit pour de la logique (il peut être
entièrement sauté, par ex. par `count()` sur une source dimensionnée depuis Java 9). (2) **Usage unique** : un
`Stream` ne peut être parcouru qu'une fois ; une seconde opération terminale lève `IllegalStateException: stream has already
been operated upon or closed` — conserver plutôt un `Supplier<Stream<T>>` ou la collection source.
(3) **Effets de bord avec les parallel streams** : `forEach(list::add)` depuis un stream parallèle mute
une `ArrayList` non thread-safe depuis plusieurs threads — éléments perdus, `null`s ou
`ArrayIndexOutOfBoundsException` ; le bon outil est `collect(...)`/`toList()`, qui construit des conteneurs par
thread et les fusionne (et voir la Q30 pour comprendre pourquoi du travail bloquant dans un stream parallèle
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

#### Q32. Comment grouper des éléments avec les streams ? {#stream-grouping-groupingby}
**Réponse :** Avec `Collectors.groupingBy(classifier)`, qui renvoie une `Map<K, List<T>>`. Sa force est le **collector
aval** (*downstream*) en second argument : au lieu d'une liste, on peut compter, sommer, extraire un champ, garder le
maximum… Et une variante à trois arguments choisit le type de `Map` (par exemple `TreeMap` pour un résultat trié).
`groupingBy` est l'équivalent du `GROUP BY` SQL : le classificateur est la clause `GROUP BY`, le collector aval est la
fonction d'agrégation (`COUNT`, `SUM`, `MAX`). Mais si les données sont en base, on fait le `GROUP BY` en SQL plutôt que de
tout charger en mémoire.

**Exemple :**

```java
record Trade(String id, String desk, String currency, BigDecimal notional, Status status) {}

// 1. Grouper simplement : Map<String, List<Trade>>
Map<String, List<Trade>> byDesk = trades.stream()
        .collect(groupingBy(Trade::desk));

// 2. Compter par groupe : Map<String, Long>
Map<String, Long> countByDesk = trades.stream()
        .collect(groupingBy(Trade::desk, counting()));

// 3. Sommer des BigDecimal par groupe (jamais summingDouble pour de l'argent)
Map<String, BigDecimal> notionalByDesk = trades.stream()
        .collect(groupingBy(Trade::desk,
                 reducing(BigDecimal.ZERO, Trade::notional, BigDecimal::add)));

// 4. Extraire un champ : Map<String, Set<String>>, les devises traitées par desk
Map<String, Set<String>> currenciesByDesk = trades.stream()
        .collect(groupingBy(Trade::desk, mapping(Trade::currency, toSet())));

// 5. Le plus gros trade par desk : Map<String, Optional<Trade>>
Map<String, Optional<Trade>> biggest = trades.stream()
        .collect(groupingBy(Trade::desk, maxBy(comparing(Trade::notional))));

// 6. Résultat trié par clé : 3e argument = fabrique de Map
TreeMap<String, Long> sorted = trades.stream()
        .collect(groupingBy(Trade::desk, TreeMap::new, counting()));

// 7. Deux niveaux : desk, puis statut
Map<String, Map<Status, List<Trade>>> byDeskAndStatus = trades.stream()
        .collect(groupingBy(Trade::desk, groupingBy(Trade::status)));

// 8. Deux groupes seulement (true / false) : partitioningBy
Map<Boolean, List<Trade>> bigOrNot = trades.stream()
        .collect(partitioningBy(t -> t.notional().compareTo(new BigDecimal("1000000")) > 0));
```

Imports utilisés : `import static java.util.stream.Collectors.*;` et `import static java.util.Comparator.comparing;`.

**`groupingBy` vs `toMap` :**

```java
// Une valeur par clé (pas une liste) : toMap
Map<String, Trade> byId = trades.stream().collect(toMap(Trade::id, Function.identity()));
// Clé en double → IllegalStateException ; fournir une fonction de fusion si c'est attendu :
Map<String, BigDecimal> totals = trades.stream()
        .collect(toMap(Trade::desk, Trade::notional, BigDecimal::add));   // équivalent du cas 3
```

**Pièges :**
- La `Map` renvoyée par `groupingBy` est une `HashMap` : **aucun ordre** garanti. Utiliser `TreeMap::new` ou
  `LinkedHashMap::new`.
- `counting()` renvoie des `Long`, pas des `Integer`.
- `summingDouble` / `averagingDouble` sur des montants : erreurs d'arrondi. Pour l'argent, `reducing` avec `BigDecimal::add`.
- Une clé `null` renvoyée par le classificateur → `NullPointerException`. `partitioningBy` renvoie toujours les deux clés,
  même vides.
- En parallèle, `groupingByConcurrent` évite la fusion coûteuse des maps (au prix de l'ordre).
- Pour lire le résultat trié par valeur (top 3 des desks) :
  `countByDesk.entrySet().stream().sorted(Map.Entry.comparingByValue(Comparator.reverseOrder())).limit(3)`.

#### Q33. Pourquoi `double` est-il inadapté à l'argent, et quels sont les pièges de `BigDecimal` une fois qu'on change ? {#double-wrong-money-bigdecimal-traps}
**Réponse :** `double` est une virgule flottante binaire : `0.1` n'a pas de représentation exacte, donc
`0.1 + 0.2 == 0.30000000000000004` et les erreurs s'accumulent à travers les sommes, remises et lignes de taxe —
un centime d'écart çà et là, ce dont les équipes de réconciliation et les auditeurs se soucient *bel et bien*.
`BigDecimal` (ou des unités mineures entières dans un `long`, c'est-à-dire des centimes) est la solution, mais
il a ses propres pièges : (1)
**`new BigDecimal(0.1)`** capture la valeur exacte du *double* (`0.1000000000000000055…`) — construire
depuis une `String` ou avec `BigDecimal.valueOf(0.1)` ; (2) **`equals()` compare le scale**, donc
`new BigDecimal("2.0").equals(new BigDecimal("2.00"))` vaut `false` — utiliser `compareTo() == 0`, et
ne jamais utiliser `BigDecimal` comme clé de `HashMap` ou dans un `HashSet` sans normaliser le scale (Q18) ;
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

**Stocker l'argent :** en base, `NUMERIC(19,4)` (ou des centimes en `long`), jamais `FLOAT`/`DOUBLE`.

#### Q34. Que garantit réellement `try-with-resources`, et sur quelle interface repose-t-il ? {#try-resources-guarantee-interface-rely}
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

#### Q35. Exceptions checked vs unchecked — quel est le véritable compromis de conception ? {#checked-unchecked-exceptions-design-trade}
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

#### Q36. Décrivez ce qui se passe réellement dans `HashMap.put()` et `.get()`, et expliquez pourquoi un mauvais `hashCode()` est un vrai bug de performance. {#happens-inside-hashmap-put-get}
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

#### Q37. Pourquoi un objet mutable avec un `hashCode()` basé sur ses champs est-il dangereux comme clé de `HashMap` ou élément de `HashSet` ? {#mutable-object-field-based-hashcode}
**Réponse :** Une `HashMap`/`HashSet` range une entrée dans un bucket en utilisant le `hashCode()` de la clé *au
moment de l'insertion* et ne le recalcule jamais (Q18). Si un champ qui participe à `hashCode()` /
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

#### Q38. Qu'est-ce qui cause `ConcurrentModificationException`, et quelle est la bonne correction ? {#causes-concurrentmodificationexception-correct-fix}
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

#### Q39. Concevez un cache LRU thread-safe et borné from scratch. Quels sont les vrais compromis ? {#design-thread-safe-bounded-lru}
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

#### Q40. Qu'est-ce qu'une race condition, un deadlock et une famine de threads, et comment reconnaître et prévenir chacun ? {#race-condition-deadlock-thread-starvation}
**Réponse :** Ce sont les trois façons classiques dont la concurrence sur état partagé tourne mal, et elles échouent
différemment. Une **race condition** est un bug où le résultat dépend d'un entrelacement malchanceux des threads : la
forme typique est *check-then-act* (`if (slot.isFree()) slot.book()`) ou *read-modify-write* (`count++`, qui fait trois
étapes, pas une). Elle produit des données fausses, pas un plantage, et seulement sous charge. On la corrige en rendant
l'action composée atomique : un verrou (`synchronized`, `ReentrantLock`), une classe atomique
(`AtomicLong.incrementAndGet`, `ConcurrentHashMap.compute`), ou en ne partageant tout simplement pas d'état mutable. Un
**deadlock** est un cycle de threads qui détiennent chacun un verrou dont le suivant a besoin, si bien que personne
n'avance ; il faut exclusion mutuelle, détention-attente, absence de préemption et attente circulaire, et en briser une
suffit, le plus simplement en acquérant toujours les verrous dans un ordre global unique, ou avec `tryLock` et un délai.
La **famine** (starvation) est un thread exécutable qui n'obtient jamais la ressource : un verrou non équitable toujours
gagné par les autres, un thread de faible priorité derrière des threads occupés, ou un pool fixe dont tous les threads
attendent des tâches placées derrière eux (*deadlock de pool*). On la prévient avec des verrous équitables là où c'est
utile, des files bornées, des pools séparés par type de charge et des délais. Diagnostic : une race ne laisse aucune trace
sauf des résultats faux (reproduire avec des tests de stress, par ex. jcstress) ; un deadlock apparaît dans un thread
dump (`jstack <pid>` affiche « Found one Java-level deadlock ») ; la famine se voit par des threads `WAITING`/`BLOCKED`,
une file qui grossit et peu de CPU.

**Exemple :**

```java
// Race condition : deux requêtes peuvent toutes deux voir le créneau libre.
if (!slot.isBooked()) { slot.book(patientId); }          // check-then-act, non atomique

// Deadlock : ordre de verrouillage inversé.
void transfer(Account a, Account b) {
    synchronized (a) { synchronized (b) { /* déplacer */ } } // T1 : (x, y)  T2 : (y, x) -> deadlock
}

// Correctif : un ordre global unique, ici par id.
void transfer(Account a, Account b) {
    Account first = a.id() < b.id() ? a : b, second = first == a ? b : a;
    synchronized (first) { synchronized (second) { /* déplacer */ } }
}
```

**Pourquoi c'est un piège :** une race condition peut survivre des années car elle exige une vraie concurrence et un
timing rare ; « ça marche sur ma machine » ne prouve rien. Et `volatile` ou une `ConcurrentHashMap` ne rendent pas une
*séquence* d'opérations atomique (voir [Java Q41](java-core-jvm.md#real-synchronized-volatile)). Les équivalents côté base de données sont traités
dans [Persistence Q26](persistence-sql-postgres.md#optimistic-pessimistic-locking-terms-contention).

#### Q41. Quelle est la vraie différence entre `synchronized` et `volatile` ? {#real-synchronized-volatile}
**Réponse :** `synchronized` fournit l'exclusion mutuelle (un seul thread exécute le bloc à la
fois) **et** une arête happens-before : tout ce qu'un thread a fait avant de relâcher un lock est visible
pour le thread suivant qui acquiert ce même lock, y compris les écritures simples (non volatile) faites
plus tôt dans le bloc. `volatile` ne fournit que *la moitié visibilité* de cela — chaque lecture d'un
champ volatile voit l'écriture la plus récente qui y a été faite, à travers les threads, et la JVM ne peut pas
réordonner d'autres opérations mémoire de part et d'autre d'une lecture/écriture volatile — sans exclusion mutuelle ; deux
threads peuvent encore se disputer pour incrémenter un `volatile int` et perdre une mise à jour, car `i++` est un
read-modify-write qui n'est pas atomique même quand le champ est volatile. Le piège senior consiste à les traiter
comme interchangeables : utiliser `volatile` pour un simple flag ou une référence quand on veut de la visibilité
sans contention (un flag d'arrêt, une référence d'instance en double-checked locking — voir Q28), et
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

#### Q42. Qu'est-ce que l'immuabilité, et pourquoi les objets immuables sont-ils si utiles dans les applications concurrentes ? {#immutability-immutable-objects-useful-concurrent}
**Réponse :** Un objet immuable ne peut plus changer après sa construction : tous les champs sont `final`, affectés dans le
constructeur, la classe ne peut pas être étendue (ou est un `record`), et aucune méthode n'expose d'état interne mutable.
Comme rien ne peut jamais changer, il n'y a rien à synchroniser : un nombre quelconque de threads peuvent lire la même
instance en même temps sans verrou, sans problème de visibilité (les champs `final` sont publiés en sécurité, voir
[Java Q43](java-core-jvm.md#safe-publication-java-memory-model)) et sans copies défensives à chaque frontière. Cela supprime des familles entières de bugs
(races, lectures déchirées, `ConcurrentModificationException`), rend les objets sûrs comme clés de `HashMap` et valeurs de
cache, et rend le raisonnement local. Le coût est l'allocation : chaque « modification » crée un nouvel objet
(`LocalDate.plusDays`, `String.concat`), ce que la JVM gère bien pour de petites valeurs mais qui est inadapté à de grosses
structures modifiées dans une boucle chaude ; on utilise alors un builder, une structure persistante ou un état mutable
confiné. Les *composants* mutables sont la fuite habituelle : `final List<Slot> slots` n'est pas immuable si la liste peut
encore être modifiée, donc on enveloppe avec `List.copyOf` en entrée et on expose `List.copyOf`/
`Collections.unmodifiableList` en sortie.

**Exemple :**

```java
public record Appointment(String id, String doctorId, Instant start, List<String> notes) {
    public Appointment {                       // constructeur compact
        notes = List.copyOf(notes);            // copie défensive : l'appelant ne pourra plus muter notre état
    }
    Appointment reschedule(Instant newStart) { // la « mutation » renvoie une nouvelle valeur
        return new Appointment(id, doctorId, newStart, notes);
    }
}
```

**Pourquoi c'est un piège :** `final` ne gèle que la *référence*, pas l'objet pointé, et un record contenant une `List` ou
une `Date` mutable n'est immuable qu'en surface. De plus, l'immuabilité protège l'objet, pas la *variable* : un
`volatile Appointment current` exige encore un remplacement atomique (`AtomicReference.compareAndSet`) quand plusieurs
threads le mettent à jour.

#### Q43. Qu'est-ce que la « safe publication » dans le Java Memory Model, et pourquoi un autre thread peut-il voir un objet à moitié construit ? {#safe-publication-java-memory-model}
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
aux autres threads un objet partiellement construit). C'est la même règle de visibilité sur laquelle s'appuient la Q28
pour le double-checked locking et la Q23 pour `volatile` ; sur x86 l'anomalie est rare à observer, ce qui est
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

#### Q44. Quand choisiriez-vous `ReentrantLock` (ou `StampedLock`) plutôt que `synchronized` ? {#pick-reentrantlock-stampedlock-synchronized}
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
JDK 21–23, `synchronized` autour d'un I/O bloquant épingle aussi un virtual thread à son carrier (Q33,
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

#### Q45. L'initialisation de classe peut-elle elle-même provoquer un deadlock, et comment se comporte l'échec d'un static initializer par la suite ? {#class-initialization-itself-deadlock-static}
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
et casser les références statiques cycliques avec un lazy holder (Q28).

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

#### Q46. Nommez les stratégies d'implémentation d'un Singleton thread-safe, et expliquez pourquoi Bill Pugh / static inner class est généralement préféré. {#name-thread-safe-singleton-implementation}
**Réponse :** Quatre approches courantes : (1) l'initialisation eager — un champ `static final`,
instancié au chargement de la classe, simple et thread-safe mais qui paie toujours le coût de construction
même s'il n'est pas utilisé ; (2) un `getInstance()` synchronized — correct mais sérialise chaque appel pour toujours,
même après l'existence de l'instance ; (3) le double-checked locking avec un champ `volatile` — lazy et
rapide après le premier appel, mais facile à rater sans `volatile` (voir Q23) ; (4) la
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

*Voir aussi :* [Design Patterns Q2](design-patterns.md#problem-singleton-solve-implement-thread) (quand un Singleton est vraiment justifié) et [Design Patterns Q16](design-patterns.md#many-senior-engineers-treat-singleton) (pourquoi c'est souvent un anti-pattern).

#### Q47. Pourquoi les `ThreadLocal`s conviennent-ils mal au code concurrent moderne, et que change `ScopedValue` ? {#threadlocal-poor-fit-modern-concurrent}
**Réponse :** Un `ThreadLocal` est un emplacement par thread, mutable et sans portée : n'importe qui peut le `set()`, il
vit jusqu'à ce que quelqu'un pense à le `remove()`, et sur un thread poolé il fait fuiter silencieusement la
valeur de la requête précédente dans la suivante (Q37). Il coûte aussi de la mémoire par thread, ce qui cesse
d'être anodin à l'échelle des virtual threads (Q33) — un million de virtual threads signifie jusqu'à un million
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

#### Q48. Quelle est la différence entre utiliser `ExecutorService` et créer des objets `Thread` bruts, et quel est un piège courant avec le common fork-join pool ? {#using-executorservice-creating-raw-thread}
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

#### Q49. Quelle est la différence entre une charge CPU-bound et I/O-bound, et comment cela change-t-il le dimensionnement des pools de threads ? {#cpu-bound-o-bound-workloads}
**Réponse :** Une tâche **CPU-bound** occupe un cœur à calculer (parsing, hachage, compression, génération de rapports) :
sa vitesse est limitée par le nombre de cœurs, donc plus de threads que de cœurs n'ajoute que des changements de contexte.
Une tâche **I/O-bound** passe l'essentiel de son temps à *attendre* (appel HTTP, requête SQL, disque, broker de
messages) : le thread est bloqué et le CPU inactif, on peut donc lancer beaucoup plus de threads que de cœurs pour occuper
le matériel. La formule classique est `threads ≈ cœurs × (1 + temps d'attente / temps de calcul)` : avec 8 cœurs et une
tâche qui attend 90 ms pour 10 ms de calcul, on obtient environ 80 threads, alors qu'une tâche purement CPU en reçoit
environ 8 (ou `cœurs + 1`). En pratique on ne mélange pas : on donne au calcul un petit pool fixe (ou
`ForkJoinPool.commonPool()` / streams parallèles) et aux I/O bloquantes leur propre pool, plus grand mais *borné*, pour
qu'une dépendance lente ne puisse ni affamer le calcul ni épuiser tous les threads. Les threads virtuels changent le côté
I/O : on peut en créer un par tâche bloquante et cesser de dimensionner le pool à la main (voir
[Java Q52](java-core-jvm.md#problem-virtual-threads-project-loom)), mais ils n'apportent rien au CPU-bound, toujours limité par les cœurs. Mesurez avant de
régler : CPU proche de 100 % avec une courte file d'exécution signale du CPU-bound ; CPU bas avec beaucoup de threads
`WAITING` et une latence croissante signale de l'I/O-bound (voir [Java Q59](java-core-jvm.md#profile-slow-cpu-hungry-java) pour le profilage).

**Exemple :**

```java
int cores = Runtime.getRuntime().availableProcessors();
ExecutorService cpuPool = Executors.newFixedThreadPool(cores);           // calcul : ~cœurs
ThreadPoolExecutor ioPool = new ThreadPoolExecutor(                       // appels bloquants : plus grand mais borné
        50, 50, 60, TimeUnit.SECONDS, new ArrayBlockingQueue<>(500),
        new ThreadPoolExecutor.CallerRunsPolicy());                       // contre-pression plutôt qu'une file non bornée

CompletableFuture.supplyAsync(() -> patientApi.fetch(id), ioPool)         // attente réseau
                 .thenApplyAsync(this::computeRiskScore, cpuPool);        // puis calcul
```

**Pourquoi c'est un piège :** un seul pool partagé pour tout laisse une rafale d'appels HTTP lents occuper tous les threads
et affamer le calcul (et les health checks) ; et `newCachedThreadPool` pour de l'I/O n'a aucune borne, si bien qu'un aval
lent finit en `OutOfMemoryError: unable to create native thread`. Voir [Java Q48](java-core-jvm.md#using-executorservice-creating-raw-thread) pour les pièges des
executors.

#### Q50. Les parallel streams : comment ça marche, et quand les utiliser ? {#parallel-streams-when-worth-it}
**Réponse :** `parallelStream()` (ou `.parallel()`) découpe la source en morceaux (via un `Spliterator`), les traite sur
plusieurs threads du **`ForkJoinPool.commonPool()`** (taille = nombre de cœurs − 1, plus le thread appelant), puis combine
les résultats. C'est rentable **seulement** pour un gros volume de calcul **CPU**, sur une source facile à découper, avec
des opérations **sans état partagé**. Dans tous les autres cas, c'est plus lent ou faux. Par défaut on reste en séquentiel :
on passe en parallèle pour un calcul CPU lourd sur une grosse collection, après mesure, et jamais pour des appels réseau.

**Exemple :**

```java
// Bon candidat : beaucoup d'éléments, calcul CPU, source découpable, aucune mutation partagée
BigDecimal totalRisk = positions.parallelStream()          // ArrayList : découpage en O(1)
        .map(riskEngine::computeVaR)                         // calcul lourd et pur
        .reduce(BigDecimal.ZERO, BigDecimal::add);           // opération associative, identité correcte

// Faux : état partagé non thread-safe
List<String> out = new ArrayList<>();
names.parallelStream().map(String::toUpperCase).forEach(out::add);   // pertes ou ArrayIndexOutOfBoundsException
List<String> ok = names.parallelStream().map(String::toUpperCase).toList();   // le collector gère la fusion

// Ordre : forEach ne respecte pas l'ordre en parallèle
IntStream.range(0, 5).parallel().forEach(System.out::print);         // ex. 31042
IntStream.range(0, 5).parallel().forEachOrdered(System.out::print);  // 01234, mais on perd une partie du gain
```

**Quand c'est rentable : la grille à donner.**

| Critère | Favorable | Défavorable |
|---|---|---|
| Volume × coût par élément | grand (règle empirique : N × Q > 10 000) | quelques centaines d'éléments simples |
| Nature du travail | CPU pur | I/O bloquante (HTTP, base, fichiers) |
| Source | `ArrayList`, tableau, `IntStream.range` | `LinkedList`, `Stream.iterate`, `BufferedReader.lines` |
| Opérations | sans état, associatives | `sorted`, `distinct`, `limit`, `findFirst` sur source ordonnée |
| Contexte | batch, calcul isolé | serveur web : le common pool est partagé par toute la JVM |

**Pièges :**
- **I/O dans un parallel stream** : les quelques threads du common pool restent bloqués, et tous les autres parallel
  streams et `CompletableFuture` sans pool explicite de l'application attendent.
- **`reduce` mal écrit** : l'identité doit être neutre. `reduce(1, Integer::sum)` en parallèle ajoute 1 par morceau. La
  fonction doit être associative (pas de soustraction).
- **Contexte de thread perdu** : `@Transactional`, `SecurityContext`, MDC des logs et `ThreadLocal` ne suivent pas sur les
  threads du pool.
- **Mesurer** avant de conclure (JMH) : le coût du découpage et de la fusion dépasse souvent le gain.
- Pool personnalisé : `customPool.submit(() -> list.parallelStream()...).get()` fonctionne, mais c'est un détail
  d'implémentation. Pour de l'I/O, utiliser plutôt des `CompletableFuture` sur un pool dédié ou des virtual threads.

Voir [Java Q31, pièges des streams](java-core-jvm.md#common-ways-stream-pipeline-goes) et
[R7, pool par défaut](java-core-jvm.md#completablefuture-create-own-thread-pool).

#### Q51. Décrivez `thenApply` vs `thenCompose` vs `thenCombine` sur `CompletableFuture`, et nommez un piège courant. {#thenapply-thencompose-thencombine-completablefuture-name}
**Réponse :** `thenApply` transforme le résultat avec une fonction simple (`T -> U`) — à utiliser quand
l'étape suivante n'est pas elle-même async. `thenCompose` aplatit une étape qui *retourne* un autre
`CompletableFuture` (`T -> CompletableFuture<U>`) — l'équivalent async de `flatMap` ; utiliser
`thenApply` ici vous donnerait un `CompletableFuture<CompletableFuture<U>>`, ce qui signifie presque toujours
que celui qui le consomme a oublié de déballer une couche. `thenCombine` joint deux futures *indépendants*
une fois les deux terminés, en exécutant une `BiFunction` sur les deux résultats. Le piège courant est d'appeler
`.get()` ou `.join()` sur un future à l'intérieur du callback d'un autre future (ou pire, sur un thread
de requête) — cela bloque un thread en attente d'un travail async, ce qui va à l'encontre de l'objectif et, sur le
common pool, risque la même famine qu'à la Q30. Composez la chaîne au lieu de bloquer en cours de route.

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

**Délais et repli :** `future.orTimeout(2, TimeUnit.SECONDS).exceptionally(ex -> fallback)` borne l'attente et fournit une
valeur de repli si l'appel échoue ou expire.

#### Q52. Quel problème les virtual threads (Project Loom) résolvent-ils réellement, et où échouent-ils encore ? {#problem-virtual-threads-project-loom}
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

#### Q53. Quand choisiriez-vous des virtual threads plutôt qu'une stack réactive (WebFlux) pour un service I/O-bound à forte concurrence, et inversement ? {#virtual-threads-reactive-stack-webflux}
**Réponse :** Les virtual threads (Q33) l'emportent quand le codebase, ses bibliothèques et son outillage de debug
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

#### Q54. Expliquez l'analyse d'accessibilité (reachability) et les GC roots, et nommez deux algorithmes de garbage collection. {#reachability-analysis-gc-roots-name}
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

#### Q55. Décrivez comment choisir entre G1, ZGC et Shenandoah pour un service sensible à la latence. {#choosing-g1-zgc-shenandoah-latency}
**Réponse :** Partez de la contrainte réelle, pas du nom du collector : G1 est le défaut sûr —
mature, bien compris, basé sur des régions, avec des objectifs de temps de pause ajustables (`-XX:MaxGCPauseMillis`) — et
convient à la plupart des services où « une pause occasionnelle de quelques dizaines de millisecondes » est acceptable. Si le
service a un budget de pause strict inférieur à 10 ms (ou à la milliseconde) quelle que soit la taille du heap — un système
de trading, un chemin de real-time bidding — ZGC et Shenandoah sont les collectors concurrents à faible pause,
qui font le marquage et le compactage en concurrence avec les threads applicatifs au lieu de stopper le monde
pour cela ; ZGC en particulier fait évoluer le temps de pause indépendamment de la taille du heap (via colored pointers
et load barriers, voir Q35), donc il reste plat même sur de très grands heaps (des centaines de Go), alors que
les pauses stop-the-world de G1 augmentent encore quelque peu avec un live set plus grand. Le compromis pour les deux
collectors concurrents est un overhead CPU un peu plus élevé (le travail concurrent entre en compétition avec les threads
applicatifs pour les cœurs) et, historiquement, un coût en débit par rapport à G1 — même si cet écart s'est réduit
de façon significative dans les versions récentes du JDK. La réponse digne d'un entretien énonce d'abord l'exigence réelle de
latence (un nombre, en millisecondes, lié à un SLO), puis choisit le collector qui y correspond,
plutôt que de partir par défaut sur « ZGC est plus récent donc meilleur » — un job ETL batch sans exigence de
latence côté utilisateur ne tire rien des faibles pauses de ZGC et paie son overhead CPU sans aucun bénéfice.

**Exemple :**

```yaml
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

#### Q56. Java a un garbage collection — comment une fuite mémoire peut-elle encore se produire ? {#java-has-garbage-collection-memory}
**Réponse :** Le GC ne récupère que les objets *inaccessibles* ; une « fuite » en Java est en réalité une accessibilité
involontaire — quelque chose détient encore une référence vers des objets dont plus personne n'a besoin, donc ils ne
deviennent jamais éligibles à la collecte. Causes classiques : une collection `static` (cache, liste de listeners) qui
ne fait que grossir et n'est jamais élaguée ; des listeners/callbacks enregistrés jamais désenregistrés, maintenant en vie
tout le graphe d'objets qu'ils capturent ; et des valeurs de `ThreadLocal` non vidées avant qu'un thread ne soit
rendu à un pool — comme les threads poolés vivent indéfiniment, tout ce qui reste dans leur map `ThreadLocal`
vit avec eux, ce qui est une fuite particulièrement vicieuse dans les thread pools d'app-server car elle est
invisible jusqu'à ce que le heap grossisse depuis des jours. Les virtual threads (Q33) ne suppriment pas ce risque ;
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

**Diagnostiquer une fuite :** `jcmd <pid> GC.heap_dump /tmp/heap.hprof`, puis Eclipse MAT (*dominator tree* et *Leak
Suspects*). Signal typique : l'Old Gen remonte après chaque full GC.

#### Q57. Quelle est la différence entre `StackOverflowError` et `OutOfMemoryError`, et d'où vient réellement chacune ? {#stackoverflowerror-outofmemoryerror-each-come}
**Réponse :** Les deux sont des `Error`s (pas des `Exception`s — la JVM signale quelque chose dont l'application
ne devrait généralement pas essayer de se remettre), mais elles viennent de régions mémoire différentes.
`StackOverflowError` se produit quand la call stack d'un seul thread dépasse sa taille fixe — presque
toujours une récursion non bornée ou excessivement profonde ; augmenter `-Xss` la retarde mais un vrai bug de
récursion infinie l'atteindra quand même tôt ou tard, simplement plus tard. `OutOfMemoryError` se produit sur
le heap (`OutOfMemoryError: Java heap space`, quand les objets vivants plus le garbage dépassent le
heap configuré et que le GC ne peut pas en libérer assez), ou dans le metaspace (`OutOfMemoryError: Metaspace`, dû au
chargement de trop de classes — un symptôme classique de fuite de classloader, voir S12), ou même à cause de trop de
threads (`OutOfMemoryError: unable to create new native thread`, atteignant une limite de threads OS,
ce qui est une raison de plus pour laquelle les virtual threads (Q33) ont changé le mode de défaillance du code à forte concurrence —
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

**Les causes typiques d'un `StackOverflowError` :**

```java
// 1. Récursion sans cas d'arrêt
static int depth(int n) { return depth(n + 1); }

// 2. Récursion correcte mais trop profonde : une liste chaînée d'un million de nœuds
static int length(ListNode n) { return n == null ? 0 : 1 + length(n.next); }

// Correction : version itérative, profondeur de stack constante
static int lengthIter(ListNode n) {
    int len = 0;
    for (; n != null; n = n.next) len++;
    return len;
}

// 3. Le cas réel le plus fréquent : relation bidirectionnelle JPA + toString/equals/JSON générés
@Entity class Order  { @OneToMany(mappedBy = "order") List<OrderLine> lines; /* toString() inclut lines */ }
@Entity class OrderLine { @ManyToOne Order order; /* toString() inclut order */ }
// order.toString() → line.toString() → order.toString() → ... → StackOverflowError
// Jackson : "Infinite recursion (StackOverflowError)" → @JsonManagedReference / @JsonBackReference, ou un DTO
```

- Java n'optimise **pas** la récursion terminale : même une récursion « en queue » consomme une frame par appel.
- Augmenter `-Xss` repousse le problème sans le régler, et multiplie la mémoire réservée par le nombre de threads.
- La trace de pile est tronquée (1 024 lignes par défaut) : chercher le motif qui se répète.
- Lombok `@Data` / `@ToString` sur des entités bidirectionnelles : exclure le côté inverse (`@ToString.Exclude`). Parcours
  d'arbres profonds : pile explicite (`ArrayDeque`). Voir aussi [Scénario S10](java-core-jvm.md#newly-deployed-feature-crashes-stackoverflowerror).

## 🔴 Expert / Ouvert

### Internes de la JVM & performance

#### Q58. Que fait le compilateur JIT, et que sont l'escape analysis et la désoptimisation ? {#jit-compiler-escape-analysis-deoptimization}
**Réponse :** La JVM commence par **interpréter** le bytecode en le profilant. Les méthodes chaudes sont compilées par
**C1** (rapide, optimisation légère), puis les plus chaudes par **C2** (ou Graal) avec des optimisations agressives
fondées sur le profil observé : **inlining** (la plus importante, elle permet toutes les autres), déroulage de boucles,
et dévirtualisation des appels d'interface qui n'ont jamais vu qu'une implémentation. L'**escape analysis** vérifie si
un objet peut sortir de la méthode ou du thread ; sinon, le JIT peut éviter de l'allouer sur le tas (**scalar
replacement**) et supprimer ses verrous. Quand une hypothèse tombe (une deuxième implémentation est chargée, une
branche « impossible » est prise), la JVM **désoptimise** vers l'interpréteur et recompile plus tard. Conséquences : la
performance demande un **warm-up** ; les micro-benchmarks sans **JMH** sont trompeurs (élimination de code mort, pas de
warm-up) ; et les sites d'appel mégamorphiques (nombreuses implémentations) sont plus lents.

**Exemple :**

```yaml
-XX:+UnlockDiagnosticVMOptions -XX:+PrintCompilation
   1203  412   4   com.acme.Pricing::finalPrice (58 bytes)        <- C2 (tier 4)
   1890  412   4   com.acme.Pricing::finalPrice   made not entrant   <- désoptimisée
```

#### Q59. Comment profiler un service Java lent ou gourmand en CPU en production ? {#profile-slow-cpu-hungry-java}
**Réponse :** Partez des métriques (CPU, temps de pause GC, taux d'allocation, pools de threads) pour savoir quelle
ressource sature. Utilisez ensuite des **profileurs à faible surcoût** utilisables en production : **Java Flight
Recorder** (intégré au JDK, environ 1 % de surcoût : `jcmd <pid> JFR.start duration=60s filename=rec.jfr`, puis
ouverture dans JDK Mission Control) donne échantillons CPU, allocations, verrous, GC et I/O ; **async-profiler** donne
des **flame graphs** CPU, allocation et verrous précis, sans biais de safepoint. Lisez le flame graph du large vers
l'étroit : les cadres larges sont là où passe le temps. Pour « c'est lent mais le CPU est bas », regardez les profils
en temps réel (wall-clock), la contention de verrous et les thread dumps (`jcmd <pid> Thread.print`) à la recherche de
threads qui attendent le pool, la base ou des verrous. Comparez avant et après un changement plutôt que de vous fier à
l'intuition.

**Exemple :**

```text
./asprof -e cpu -d 30 -f cpu.html <pid>
flame graph : 41 % dans com.fasterxml.jackson...serialize  <- sérialisation d'une réponse de 5 Mo par requête
./asprof -e alloc -d 30 -f alloc.html <pid>
```

#### Q60. GraalVM native image vs une JVM classique — quand cela en vaut-il la peine ? {#graalvm-native-image-regular-jvm}
**Réponse :** Native image compile l'application à l'avance en un exécutable autonome, sous une **hypothèse de monde
fermé** : tout ce qui est atteignable doit être connu au build. Gains : démarrage en dizaines de millisecondes et
empreinte mémoire bien plus faible, ce qui convient aux fonctions serverless, aux CLI et aux charges qui descendent à
zéro. Coûts : builds longs, réflexion, proxies et ressources à déclarer (l'AOT de Spring Boot 3 génère la plupart des
hints, mais les bibliothèques sans métadonnées demandent une configuration manuelle), débit maximal inférieur à un JIT
C2 chaud sauf avec l'optimisation guidée par profil, et un runtime différent à déboguer et superviser. Pour des
services longue durée sur Kubernetes, une JVM classique avec **Class Data Sharing (AppCDS)**, le checkpoint/restore
**CRaC**, ou le cache AOT de Leyden dans les JDK récents apporte souvent l'essentiel du gain au démarrage avec moins de
contraintes.

#### Q61. Comment fonctionne le chargement de classes, et qu'apporte JPMS (les modules) ? {#class-loading-jpms-modules-add}
**Réponse :** Les classes sont chargées paresseusement par une hiérarchie de class loaders : **bootstrap** (cœur du
JDK), **platform** et **application** (votre classpath), avec **délégation au parent** (on demande d'abord au parent).
Les serveurs d'applications, les fat jars Spring Boot et les systèmes de plugins ajoutent leurs propres loaders. Une
classe est identifiée par son nom **et** son loader, d'où les « `ClassCastException`: com.acme.Foo cannot be cast to
com.acme.Foo » (deux loaders ont chargé la même classe), et d'où les fuites mémoire au redéploiement dans un conteneur,
via un class loader maintenu en vie par un thread ou une référence statique. **JPMS** (modules Java 9) ajoute une
**encapsulation forte** : un `module-info.java` déclare ce qu'il `requires` et quels packages il `exports` ; les packages
non exportés sont inaccessibles même s'ils sont publics, et la réflexion exige `opens`. Il détecte au démarrage les
packages scindés et les dépendances manquantes. La plupart des applications Spring tournent encore sur le classpath,
mais c'est JPMS qui garde les internes du JDK fermés (d'où les options `--add-opens`) et permet des runtimes minimaux
avec `jlink`.

**Exemple :**

```java
module com.acme.billing {
    requires java.sql;
    exports com.acme.billing.api;          // API publique
    opens com.acme.billing.model to com.fasterxml.jackson.databind;   // réflexion pour Jackson seulement
}
```

#### Q62. Pourquoi les images natives consomment-elles si peu de mémoire et démarrent-elles si vite, et que sacrifie-t-on ? {#native-images-little-memory-start}
**Réponse :** Une JVM classique fait à l'exécution ce qu'une image native a fait une seule fois au build. Au démarrage,
la JVM charge et vérifie les classes, interprète le bytecode, le profile, puis compile les méthodes chaudes avec C1/C2
sur des threads d'arrière-plan ; cela coûte du temps (de centaines de ms à plusieurs secondes) et de la mémoire
(Metaspace pour les métadonnées de classes, code cache du JIT, données de profilage, threads du compilateur et leur
mémoire de travail, souvent 100-300 Mo en plus du heap). **Native Image** déplace ce travail au build : une **analyse de
points-to** trouve tout ce qui est atteignable depuis `main` (le *monde fermé*) et **supprime le reste** (classes,
méthodes inutilisées, même des parties du JDK) ; certaines classes sont **initialisées au build** et le graphe d'objets
obtenu est écrit dans l'exécutable sous forme de **snapshot du heap de l'image**, donc l'application démarre avec son état
déjà construit ; le code est du code machine dès le départ (ni interpréteur, ni JIT, ni warm-up), et un petit runtime
(« Substrate VM ») avec un **Serial GC** simple et un petit heap par défaut remplace HotSpot. Résultat : typiquement
~20-50 ms de démarrage et une mémoire résidente plusieurs fois plus faible que la même application sur JVM.
Ce que l'on sacrifie : le **débit maximal** (C2 optimise avec de vrais profils d'exécution ; le code natif est compilé à
l'aveugle sauf si on lui fournit un profil via la **PGO**, Oracle GraalVM), le **temps et la RAM de build** (minutes et
plusieurs Go par build), les **fonctionnalités dynamiques** (réflexion, proxies, ressources et JNI doivent être connus au
build) et l'**outillage** (pas de parité JFR/attach/`jcmd`, débogage différent). C'est une optimisation de démarrage et
d'empreinte, pas une accélération générale.

**Exemple :**

```bash
# Même service Spring Boot, mesuré après démarrage + une requête (valeurs indicatives)
java -jar app.jar          # démarrage ~2,5 s   RSS ~380 Mo
./target/app               # démarrage ~0,05 s  RSS ~70 Mo
ps -o rss= -p <pid>        # mémoire résidente en Ko
```

#### Q63. Comment construit-on une application Spring Boot 3 en image native, étape par étape ? {#build-spring-boot-3-application}
**Réponse :**

1. **Installer un JDK GraalVM** (21+ pour Boot 3.x) et le vérifier : `sdk install java <version-graalvm>`, puis
   `java -version` et `native-image --version` (Oracle GraalVM pour la PGO et G1 ; GraalVM CE sinon).
2. **Utiliser le build AOT de Spring Boot.** `spring-boot-starter-parent` définit déjà le profil `native` et enregistre
   `native-maven-plugin` ; Gradle demande le plugin `org.graalvm.buildtools.native`. Au build, Spring exécute le
   **traitement AOT** : il évalue les conditions et génère le code des définitions de beans ainsi que les **hints**
   de réflexion/proxy/ressources, au lieu de les découvrir à l'exécution.
3. **Construire l'exécutable :** `mvn -Pnative native:compile` (Gradle : `./gradlew nativeCompile`). Le binaire arrive
   dans `target/` ; comptez quelques minutes et 4-8 Go de RAM.
4. **Ou construire directement une image de conteneur** avec les Cloud Native Buildpacks, sans GraalVM local :
   `mvn -Pnative spring-boot:build-image` (Gradle : `./gradlew bootBuildImage`).
5. **Corriger les métadonnées manquantes.** Tout ce qui est résolu dynamiquement (réflexion, mapping JSON de vos propres
   classes, resource bundles, `Class.forName`, proxies JDK) doit être déclaré. Premier choix : les hints de Spring
   (`@RegisterReflectionForBinding`, `@ImportRuntimeHints` avec un `RuntimeHintsRegistrar`) ; pour les bibliothèques,
   le **dépôt de métadonnées d'atteignabilité GraalVM** (récupéré automatiquement par le plugin) ; en dernier recours :
   lancer l'application sur la JVM avec l'**agent de traçage** pour générer la config JSON, puis ne garder que
   l'utile.
6. **Tester en mode natif**, pas seulement sur la JVM : `mvn -PnativeTest test` (Gradle : `./gradlew nativeTest`)
   exécute la suite de tests compilée en image native ; lancer le binaire produit avec un smoke test en CI.
7. **L'expédier léger.** Un Dockerfile multi-étapes qui copie le binaire dans une base minimale (distroless/`scratch`
   avec liaison statique ou quasi statique : `--static --libc=musl` ou `--static-nolibc`). Limiter la mémoire avec les
   options natives (`-Xmx`, `-Xms` sont supportées par le Serial GC de l'image) et comparer RSS et démarrage à la
   référence JVM.
8. **Ne régler que si nécessaire :** mode build rapide `-Ob` en dev, `-O3`/**PGO** en production pour le débit
   (`--pgo-instrument`, charge représentative, rebuild avec `--pgo=default.iprof`), `--gc=G1` sur Oracle GraalVM quand
   les pauses du Serial GC gênent sur de plus gros heaps.

**Exemple :**

```xml
<!-- pom.xml : le parent fournit déjà le profil "native" ; les arguments de build supplémentaires vont ici -->
<plugin>
  <groupId>org.graalvm.buildtools</groupId>
  <artifactId>native-maven-plugin</artifactId>
  <configuration>
    <buildArgs>
      <buildArg>-Ob</buildArg>   <!-- builds de dev plus rapides ; à retirer en production -->
    </buildArgs>
  </configuration>
</plugin>
```

```java
@Configuration
@ImportRuntimeHints(AcmeHints.class)
class NativeConfig {}

class AcmeHints implements RuntimeHintsRegistrar {
    public void registerHints(RuntimeHints hints, ClassLoader cl) {
        hints.reflection().registerType(InvoiceDto.class, MemberCategory.values()); // lu par Jackson via la réflexion
        hints.resources().registerPattern("templates/*.html");                      // chargé depuis le classpath
    }
}
```

```bash
# Générer les hints d'une bibliothèque sans métadonnées : exercer l'application sur la JVM avec l'agent
java -agentlib:native-image-agent=config-output-dir=src/main/resources/META-INF/native-image -jar app.jar
```

## 🎯 Scénarios réels

### S1. Un service de production lève `OutOfMemoryError: Java heap space` après un pic de trafic {#production-service-throws-outofmemoryerror-java}
- **Symptômes :** Le service était sain pendant des semaines, puis lors d'un pic de trafic lié à une campagne marketing
  il se met à lever `OutOfMemoryError: Java heap space` et est OOMKilled ou redémarré par
  l'orchestrateur.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S2. L'application se fige plusieurs secondes d'affilée, apparemment au hasard {#app-freezes-several-seconds-time}
- **Symptômes :** Pas d'erreurs, pas de crashs, mais les graphes de latence montrent des pics périodiques où chaque
  requête se bloque pendant 2 à 5 secondes simultanément, puis récupère.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Ce schéma — tout se met en pause en même temps — est la signature d'une pause GC
  stop-the-world, pas de la logique applicative. Activer/consulter les logs GC (`-Xlog:gc*`) et corréler les
  horodatages des pauses avec les pics de latence ; s'ils coïncident, c'est confirmé.
- **Exemple :**

  ```text
  [12.481s][info][gc] GC(42) Pause Full (Allocation Failure) 1998M->1950M(2048M) 2412.331ms
  ```

  Une ligne `Pause Full` de plus de 2 secondes coïncidant exactement avec un pic de latence de requête au même
  horodatage est la preuve qui confirme — pas une coïncidence à balayer.

- **Résolution :** Selon ce que montre le log GC : si les pauses sont corrélées à des full GCs, la
  young generation est peut-être sous-dimensionnée (trop d'objets promus trop tôt) — ajuster le
  dimensionnement des générations avant de changer de collector. Si les pauses sont fréquentes mais que l'objectif de temps de pause
  lui-même est trop lâche, resserrer `-XX:MaxGCPauseMillis`. Si le service a un budget de latence réellement strict
  que le collector actuel ne peut atteindre même ajusté, c'est le cas pour passer à ZGC/Shenandoah (Q36).
- **Prévention :** Envoyer les métriques de pauses GC sur le même dashboard que la latence des requêtes pour que cette
  corrélation soit une vérification de cinq secondes la prochaine fois, et non une nouvelle investigation ; définir un SLO de temps de
  pause GC à côté du SLO de latence des requêtes.

</details>

### S3. `ConcurrentModificationException` apparaît par intermittence dans les logs de production {#concurrentmodificationexception-appears-intermittently-production-logs}
- **Symptômes :** Un job en arrière-plan ou un handler de requête lève occasionnellement
  `ConcurrentModificationException`, mais ce n'est pas reproductible en local et cela n'arrive pas à
  chaque exécution.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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
  passer à `Iterator.remove()` ou `removeIf` (Q20). Si c'est un accès inter-threads à un état mutable partagé,
  c'est le vrai bug — soit rendre l'accès mono-thread (en passant par un seul
  executor), soit passer à une collection concurrente adaptée au schéma d'accès
  (`ConcurrentHashMap`, `CopyOnWriteArrayList` pour lecture majoritaire/écriture rare, ce qui convient bien à une liste de
  listeners puisque l'enregistrement est rare et la notification fréquente).
- **Prévention :** Traiter toute collection mutable accessible depuis plus d'un thread comme un
  point d'attention en code review ; documenter la propriété (quel thread/composant a le droit de la muter) directement
  dans la déclaration du champ.

</details>

### S4. Une recherche basée sur `HashMap` qui était rapide est devenue de plus en plus lente au fil des mois {#hashmap-backed-lookup-used-fast}
- **Symptômes :** Un cache ou un index indexé par un type d'objet personnalisé était rapide au lancement ; les temps de réponse
  de cette recherche ont dérivé à mesure que le jeu de données grossissait, de façon disproportionnée par rapport à la croissance du nombre
  d'entrées.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Vérifier l'implémentation de `hashCode()` du type de clé (Q18). Un bug courant :
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

</details>

### S5. L'usage du heap grimpe régulièrement et ne redescend jamais, même sous faible charge {#heap-usage-climbs-steadily-never}
- **Symptômes :** L'usage du heap après chaque cycle GC tend à monter sur plusieurs jours, sans lien avec le trafic
  actuel — un classique motif en dents de scie qui ne se réinitialise jamais sur le graphe mémoire.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

- **Voir aussi :** [Design Patterns S2](design-patterns.md#heap-usage-climbs-steadily-days), même symptôme avec une autre cause (une liste d'Observers jamais désabonnés).
- **Résolution :** Ajouter une borne/de l'éviction à la collection fautive (plafond de taille, TTL, ou passage à
  une vraie bibliothèque de cache), ou corriger la logique sous-jacente si les entrées auraient dû être retirées sur
  un événement de cycle de vie qui ne se déclenche pas (par ex. un listener jamais désenregistré — voir Q37).
- **Prévention :** Interdire par défaut en code review les collections mutables `static` non bornées ; exiger que
  tout cache en mémoire intentionnel énonce explicitement sa borne et sa politique d'éviction.

</details>

### S6. Le CPU reste collé près de 100 % sans augmentation proportionnelle du volume de requêtes {#cpu-sits-pegged-near-100}
- **Symptômes :** L'utilisation CPU monte et reste haute alors que le débit de requêtes reste plat ou
  baisse ; le service répond toujours techniquement, mais lentement.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S7. Sous charge, les requêtes commencent à expirer alors que les dépendances aval sont saines {#under-load-requests-start-timing}
- **Symptômes :** La latence et le taux d'erreurs grimpent fortement au-delà d'un certain seuil de requêtes concurrentes,
  alors que la base de données/les services aval affichent des temps de réponse normaux sur leurs propres
  dashboards.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Thread dump pendant le ralentissement ; chercher de nombreux threads `WAITING` sur la file de l'executor
  plutôt qu'en exécution active — c'est de l'épuisement de thread pool, des requêtes qui font la queue derrière un
  pool de taille fixe plutôt qu'un aval lent. Comparer la taille configurée du pool à la
  demande concurrente réelle, et vérifier si un handler fait du travail bloquant sur un pool dimensionné
  pour autre chose (le piège du common pool de la Q30, ou le pool de traitement des requêtes d'un serveur web utilisé
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
  le travail I/O-bound (Q33).
- **Prévention :** Exposer la profondeur de la file de l'executor et le nombre de threads actifs comme métriques, pas seulement la
  latence des requêtes — une profondeur de file qui grimpe alors que la latence aval est plate est le signal spécifique
  de ce mode de défaillance, et il est invisible sans cette métrique.

</details>

### S8. Deux services (ou deux chemins de code) se bloquent occasionnellement en deadlock et cessent de progresser {#two-services-two-code-paths}
- **Symptômes :** Un sous-ensemble de requêtes se bloque simplement pour toujours — pas d'erreur, aucun timeout ne se déclenche, pas de
  crash — jusqu'au redémarrage du processus.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S9. Une comparaison de deux montants est correcte en test mais silencieusement fausse en production {#comparison-two-amounts-correct-testing}
- **Symptômes :** Une comparaison entre deux valeurs `Integer` se comporte correctement en test (petites
  valeurs) mais se comporte mal par intermittence en production avec des nombres réels (plus grands) — une logique qui
  devrait être équivalente à une comparaison numérique prend silencieusement la mauvaise branche.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Faire un grep du chemin de code pour `==` entre types boxés (`Integer`, `Long`) ; c'est le
  piège du cache d'autoboxing de la Q9 — les valeurs dans `[-128, 127]` sont par hasard `==`-égales par
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

</details>

### S10. Une fonctionnalité fraîchement déployée plante avec `StackOverflowError` pour un sous-ensemble d'utilisateurs {#newly-deployed-feature-crashes-stackoverflowerror}
- **Symptômes :** Des erreurs n'apparaissent que pour certaines entrées (par ex. fils de commentaires profondément imbriqués, grands
  arbres de catégories) juste après la livraison d'une fonctionnalité qui traite un arbre ou un graphe récursivement.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S11. Après la migration d'un service vers les virtual threads, le débit de type thread-pool se dégrade en réalité sous charge {#after-migrating-service-virtual-threads}
- **Symptômes :** Après la migration vers les virtual threads, le service dont on attendait une meilleure scalabilité
  montre au contraire de la contention sur les carrier threads — le débit plafonne bien en dessous des attentes, et
  les thread dumps montrent de nombreux virtual threads bloqués plutôt qu'en progression.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Chercher des blocs ou méthodes `synchronized` sur le hot path (Q33). Tant que le pinning
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

</details>

### S12. L'usage du metaspace grossit à chaque redéploiement de l'application sur un app server de longue durée {#metaspace-usage-grows-every-time}
- **Symptômes :** `OutOfMemoryError: Metaspace` après plusieurs redéploiements sur la même instance JVM
  (une configuration d'app server à hot-redeploy), alors que le code applicatif lui-même n'a pas
  visiblement grossi.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** C'est une fuite de classloader — chaque redéploiement devrait laisser le classloader de l'ancienne application
  (et chaque classe qu'il a chargée) devenir du garbage une fois la nouvelle version en ligne, mais
  quelque chose détient encore une référence vers l'ancien classloader, donc aucune de ses classes n'est jamais
  déchargée et le metaspace accumule une copie complète des métadonnées de classes par redéploiement. Suspects
  habituels : un driver JDBC enregistré via `DriverManager` et jamais désenregistré, un `ThreadLocal`
  contenant une instance d'une classe applicative sur un thread de pool de longue durée (Q37), ou une
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

</details>

### S13. Sous charge, un service « singleton » est parfois construit plus d'une fois, causant des effets de bord en double {#under-load-singleton-service-occasionally}
- **Symptômes :** Un composant censé être une instance partagée unique (par ex. l'initialisation d'un registre de métriques,
  l'ouverture d'un connection pool) logue parfois son message « initializing » deux fois sous charge
  de démarrage concurrent, et des symptômes de ressources en double s'ensuivent en aval (métriques enregistrées deux fois,
  connection pool doublé).

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

- **Résolution :** Passer au pattern static-holder-class de Bill Pugh (Q28), dont la JVM
  garantit qu'il est thread-safe sans aucune synchronisation nécessaire, ou ajouter `volatile` si le double-checked
  locking doit être conservé pour une raison quelconque.
- **Prévention :** Adopter par défaut le pattern static-holder (ou un singleton `enum`) pour tout
  singleton fait main plutôt que le double-checked locking — c'est strictement plus simple et supprime
  toute cette classe de défaillances.

</details>

### S14. Les temps de pause GC se dégradent nettement juste après une mise à niveau du JDK/du collector {#gc-pause-times-get-noticeably}
- **Symptômes :** Après la mise à niveau de la version du JDK (ou le changement de collector par défaut), la latence p99
  régresse alors que le débit et le CPU semblent similaires à avant.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Comparer les logs GC avant et après ; une cause courante est que les flags de dimensionnement du heap
  (`-Xmx`, `-Xms`, ratios de générations) réglés pour le comportement de l'ancien collector ne se transposent pas
  proprement aux défauts du nouveau — par ex. la taille de région de G1 et l'objectif de temps de pause interagissent
  différemment avec une taille de heap donnée que le collector qu'il a remplacé.
- **Exemple :**

  ```text
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

</details>

### S15. Les `NullPointerException`s explosent juste après la mise à niveau d'une dépendance de bibliothèque {#nullpointerexception-spike-sharply-right-after}
- **Symptômes :** Un service auparavant stable commence à lever des `NullPointerException` à plusieurs
  endroits d'appel sans rapport immédiatement après le bump de version d'une dépendance, sans aucun changement de code
  applicatif.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S16. Le débit plafonne sous forte concurrence alors que le CPU a de la marge {#throughput-flattens-under-high-concurrency}
- **Symptômes :** Ajouter plus de charge concurrente n'augmente pas le débit au-delà d'un certain point, et
  l'utilisation CPU reste bien en dessous de 100 % — le système n'est pas limité par le calcul, mais il ne
  passe pas non plus à l'échelle.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S17. La latence grimpe à plusieurs minutes pendant un ralentissement aval, puis le service meurt avec `OutOfMemoryError` {#latency-climbs-minutes-during-downstream}
- **Symptômes :** Un service de notification de paiement répond normalement en 40 ms. Quand une API partenaire
  se met à répondre en 3 s au lieu de 100 ms, le p99 de *notre* endpoint dépasse 60 s en quelques
  minutes — bien après que le partenaire a récupéré — et finalement les pods sont OOMKilled. Le CPU est bas
  tout du long, et le nombre de threads ne grossit jamais.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** CPU bas plus nombre de threads plat signifie que le travail *attend*, sans s'exécuter. Un thread
  dump (`jcmd <pid> Thread.print`, pris deux fois à ~10 s d'intervalle) montre les 8 threads du pool bloqués dans le
  même appel HTTP partenaire. L'indice est la file : exposer
  `ThreadPoolExecutor.getQueue().size()` (ou `ExecutorServiceMetrics` de Micrometer, c'est-à-dire
  `executor.queued`) montre des centaines de milliers et en croissance, et un histogramme du heap
  (`jmap -histo:live <pid>`) est dominé par des instances de `FutureTask` / lambda. La cause est
  `Executors.newFixedThreadPool(8)` : sa file est une `LinkedBlockingQueue` *non bornée*, donc il ne
  dit jamais « non » — chaque tâche soumise attend son tour derrière tout ce qui la précède, ce qui transforme un
  ralentissement transitoire en minutes de latence puis en épuisement du heap (Q30).
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

</details>

### S18. Les dates sont parfois fausses, ou le parsing lève de bizarres `NumberFormatException`s, uniquement sous charge {#dates-occasionally-wrong-parsing-throws}
- **Symptômes :** Un job d'import et une API partagent un utilitaire qui formate et parse des dates.
  Parfois une facture est estampillée avec la date d'une *autre* ligne, et les logs montrent
  `NumberFormatException: multiple points`, `ArrayIndexOutOfBoundsException`, ou
  `NumberFormatException: For input string: ""`. Cela ne se reproduit jamais avec une seule requête.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Des erreurs bizarres, non déterministes et *corrélées à la charge* sont la
  signature d'un état mutable partagé. Faire un grep de `SimpleDateFormat` (et `DecimalFormat`,
  `NumberFormat`) dans un champ `static final` — ils contiennent un `Calendar` interne et des buffers de travail
  réécrits à chaque appel, donc deux threads appelant `format()`/`parse()`
  concurremment corrompent l'état intermédiaire l'un de l'autre. `SimpleDateFormat` est documenté comme non
  thread-safe ; le bug n'apparaît que lorsque deux appels se chevauchent réellement (Q23).
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

</details>

### S19. Le pod est OOMKilled alors que le dashboard du heap n'en montre qu'environ 40 % utilisé {#pod-oomkilled-although-heap-dashboard}
- **Symptômes :** Une gateway basée sur Netty avec `-Xmx2g` dans un conteneur de 3 GiB redémarre toutes les quelques
  heures avec `OOMKilled` (exit 137, Kubernetes affiche `Reason: OOMKilled`). Pas d'
  `OutOfMemoryError` dans les logs, aucun heap dump écrit, et le graphe du heap est confortablement
  en dessous de la limite à chaque redémarrage.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S20. Un job planifié se déclenche une heure trop tôt, deux fois, ou pas du tout le week-end du changement d'heure {#scheduled-job-fires-hour-early}
- **Symptômes :** Un job de règlement quotidien à 02:30 et une fonctionnalité « expire dans 24 heures » fonctionnent toute l'année,
  puis le dernier dimanche de mars il ne s'exécute pas du tout, et le dernier dimanche d'octobre il
  s'exécute deux fois. Des clients d'une région voient aussi des heures d'expiration décalées d'une heure.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

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

</details>

### S21. Un job de « nettoyage » dit avoir supprimé les sessions expirées, pourtant la mémoire continue de croître et des sessions périmées apparaissent encore {#cleanup-job-says-removed-expired}
- **Symptômes :** Un `HashSet<Session>` suit les sessions actives. Une tâche planifiée appelle
  `remove()` sur les expirées et logue `removed=true`, mais le `size()` du set continue de monter, l'usage du heap
  grimpe régulièrement, et certains utilisateurs sont encore traités comme connectés après déconnexion. Aucune exception
  nulle part.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** `size()` grossit alors que `remove()` ne réussit que pour *certains* éléments, donc
  suspecter le hashing : un élément qui ne peut plus être retrouvé par son propre hash. Un heap dump montre le
  set contenant bien plus d'objets `Session` que n'en justifie toute logique métier ; itérer et
  appeler `set.contains(each)` dessus renvoie `false` pour beaucoup. C'est le motif de la Q19 —
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

</details>

### S22. Le service se bloque au démarrage environ un déploiement sur vingt, sans erreur et sans usage CPU {#service-hangs-startup-roughly-one}
- **Symptômes :** Après un déploiement, une instance reste « starting » pour toujours : la readiness probe ne
  passe jamais, le CPU est proche de 0, et les logs s'arrêtent en plein démarrage sans exception. Redémarrer le pod règle le problème,
  ce qui en fait une légende de déploiement instable plutôt qu'un ticket. Cela arrive plus souvent quand
  l'instance démarre avec plus de CPU disponibles (plus de threads de démarrage parallèles).

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Prendre deux thread dumps (`jcmd <pid> Thread.print`) à quelques secondes d'intervalle et les comparer.
  Deux threads applicatifs sont bloqués avec la frame `at com.acme.Catalog.<clinit>` /
  `at com.acme.Pricing.<clinit>`, chacun attendant que la classe de l'autre finisse de s'initialiser.
  `<clinit>` est l'indice : c'est le deadlock d'initialisation de classe de la Q27, et le rapport standard de la JVM
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
  classe : rendre un côté lazy (un holder Bill Pugh, Q28) ou injecter la dépendance à l'exécution
  au lieu de la résoudre dans un bloc `static` ; sortir tout I/O ou câblage de `<clinit>`. En
  palliatif, forcer un ordre d'initialisation fixe au démarrage depuis un seul thread (toucher `Catalog`
  avant de démarrer le travail parallèle). Vérifier en exécutant le démarrage 200 fois en boucle dans la CI avec
  l'init parallèle activée — un deadlock qui apparaît 1 fois sur 20 se manifestera en quelques exécutions.
- **Prévention :** Les static initializers doivent être triviaux : constantes et construction pure uniquement, pas de
  références statiques inter-classes en cycle, pas de threads, pas d'I/O. Ajouter un test de watchdog de démarrage qui
  échoue si l'application n'est pas prête dans une limite donnée, et capturer un thread dump automatiquement quand
  la readiness expire pour que la prochaine occurrence s'explique d'elle-même.

</details>

### S23. Le service fonctionne sur la JVM mais échoue en image native avec `NoSuchMethodException` ou un JSON vide {#service-jvm-but-fails-native}
- **Symptômes :** Après le passage du build en image native, l'application démarre vite mais un endpoint renvoie `{}`
  ou une `500` avec `NoSuchMethodException` / `ClassNotFoundException` / « no serializer found ». Le même code et les
  mêmes tests passent sur une JVM classique, et le chemin en échec n'est emprunté que par certaines requêtes.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher le diagnostic, la résolution et la prévention</summary>

- **Diagnostic :** L'analyse en monde fermé a supprimé ou n'a pas enregistré un élément uniquement atteint par
  **réflexion**, **proxy dynamique**, **recherche de ressource** ou `Class.forName` ; la JVM le résout à l'exécution,
  l'image native ne le peut pas. Lire la première ligne de la stack trace : la classe ou le membre manquant y est nommé.
  Reproduire sur la JVM avec l'agent de traçage (`-agentlib:native-image-agent=...`) en exerçant cet endpoint, et
  comparer le `reflect-config.json` généré avec ce que le build contient déjà.
- **Exemple :**

  ```java
  record InvoiceDto(String id, BigDecimal total) {}      // uniquement touché par Jackson, via la réflexion

  // Correctif : en informer le moteur AOT
  @RegisterReflectionForBinding(InvoiceDto.class)
  @RestController class InvoiceController { /* ... */ }
  ```

- **Résolution :** Enregistrer le type avec les hints de Spring (`@RegisterReflectionForBinding`,
  `RuntimeHintsRegistrar`) ou les métadonnées de la bibliothèque ; mettre à jour la bibliothèque si une version plus
  récente fournit des métadonnées d'atteignabilité. Éviter `Class.forName` avec des noms calculés et le scan du
  classpath dans son propre code.
- **Prévention :** Exécuter les tests d'intégration en mode natif en CI (`mvn -PnativeTest test`) avec un smoke test qui
  appelle chaque endpoint, afin qu'un hint manquant fasse échouer le build plutôt que la production. Préférer les
  bibliothèques connues pour supporter le natif.

</details>

### S24. Le build natif manque de mémoire ou dure plus de 20 minutes en CI {#native-build-runs-out-memory}
- **Symptômes :** `mvn -Pnative native:compile` est tué dans le pipeline (code 137 ou « OutOfMemoryError during image
  generation »), ou réussit mais chaque build prend 15-25 minutes et bloque chaque merge.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher le diagnostic, la résolution et la prévention</summary>

- **Diagnostic :** Le compilateur natif fait une analyse de programme entier puis la génération de code dans un processus
  séparé, qui demande plusieurs Go de RAM et est limité par le CPU. Comparer la limite mémoire du runner au pic RSS
  rapporté par le builder (`--emit build-report`, ou `-H:+PrintAnalysisCallTree` pour creuser) et vérifier si un arbre de
  dépendances énorme gonfle l'atteignabilité.
- **Exemple :**

  ```bash
  # pom.xml <buildArgs> : plafonner le heap du builder, mode rapide pour les builds hors release
  <buildArg>-J-Xmx8g</buildArg>
  <buildArg>-Ob</buildArg>
  mvn -Pnative native:compile
  ```

- **Résolution :** Donner au job un runner avec 8 Go+ et plus de cœurs ; utiliser `-Ob` (build rapide) pour les builds
  de PR et le build entièrement optimisé seulement pour la release ; ne construire l'image native **que sur main/tag**,
  les PR exécutant les tests JVM et `nativeTest` de façon planifiée ; mettre en cache le dépôt Maven/Gradle. Retirer les
  dépendances inutilisées, chacune agrandit l'analyse.
- **Prévention :** Traiter le natif comme un artefact de release : un build optimisé par release candidate, une taille de
  runner dédiée et un budget de temps de build suivi comme n'importe quel SLO de pipeline.

</details>

### S25. Après le passage au natif, la mémoire a baissé mais le débit et la latence de queue sous charge soutenue se sont dégradés {#after-moving-native-memory-dropped}
- **Symptômes :** Une API très sollicitée en image native utilise 5x moins de mémoire et démarre instantanément, mais à
  charge élevée stable son p99 et ses requêtes/seconde sont pires que l'ancien déploiement JVM, et des pauses GC
  apparaissent sur un heap plus grand.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher le diagnostic, la résolution et la prévention</summary>

- **Diagnostic :** C'est le compromis attendu, pas un bug. Le compilateur **C2** d'une JVM chaude optimise avec de vrais
  profils d'exécution (inlining, spéculation), alors que l'image native a été compilée à l'avance sans ces données. Côté
  GC, GraalVM CE utilise le **Serial GC** (mono-thread, stop-the-world), qui souffre quand le heap et le taux
  d'allocation augmentent. Comparer le **même test de charge** sur les deux artefacts et regarder les logs GC
  (`-XX:+PrintGC` dans l'image) et le CPU.
- **Exemple :**

  ```bash
  # Oracle GraalVM : optimisation guidée par profil + collecteur parallèle (<buildArg> du pom.xml)
  --pgo-instrument                     # build 1 : binaire instrumenté
  ./target/app                         # charge représentative -> default.iprof
  --pgo=default.iprof  --gc=G1         # build 2 : optimisé avec le profil
  ```

- **Résolution :** Si le service est longue durée et limité par le débit, **rester sur la JVM** (éventuellement avec
  AppCDS ou CRaC pour le démarrage). Si le natif reste souhaité pour l'empreinte, ajouter la PGO et `--gc=G1`, et
  dimensionner le heap explicitement.
- **Prévention :** Décider avec un benchmark de votre propre charge avant de migrer ; adopter le natif pour des problèmes
  de démarrage/d'empreinte (serverless, scale-to-zero, nombreuses petites instances), pas comme accélération générique.

</details>

### S26. Les cold starts Lambda atteignent 6 secondes : faut-il passer la fonction Spring Boot en image native ? {#lambda-cold-starts-hit-6}
- **Symptômes :** Une Lambda Java derrière API Gateway affiche des cold starts de 5-6 s et les utilisateurs remarquent la
  première requête après inactivité. L'équipe propose de réécrire en Go ; vous suggérez de garder Java.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher le diagnostic, la résolution et la prévention</summary>

- **Diagnostic :** Cold start = init du runtime + chargement de classes + démarrage du framework + warm-up du JIT.
  Mesurer la durée d'init dans les logs Lambda (`Init Duration`) et ce que fait le framework au démarrage (scan de
  beans, clients du SDK AWS, gros classpath). Les options échangent effort contre gain : classpath réduit et init
  paresseuse (faible effort) ; **SnapStart** (restaure un snapshot de la JVM initialisée, sans changement de build, avec
  ses propres précautions sur l'unicité et les connexions) ; **image native** (meilleur cold start et mémoire, coût de
  build et de compatibilité le plus élevé).
- **Exemple :**

  ```yaml
  # SAM : essayer SnapStart d'abord, il ne demande pas de build natif
  Resources:
    Fn:
      Type: AWS::Serverless::Function
      Properties:
        Runtime: java21
        SnapStart: { ApplyOn: PublishedVersions }
  ```

- **Résolution :** Mesurer, puis escalader : init paresseuse et dépendances plus légères, puis SnapStart ; passer au natif
  quand le démarrage doit tenir en dizaines de ms ou quand la mémoire allouée (facturée au Go-s) peut baisser nettement.
  Pour le natif, utiliser un runtime personnalisé ou le Lambda web adapter et exécuter `nativeTest` en CI.
- **Prévention :** Suivre le cold start et le p99 comme métriques de release, garder des fonctions petites et
  mono-usage, et réévaluer la décision quand le JDK livre de meilleures fonctions de démarrage (CRaC, cache AOT Leyden).

</details>

## 🗣️ Questions posées en entretien

Questions rapportées d'entretiens réels, regroupées par sujet. Chacune a une courte réponse type : approfondissez avec les questions et scénarios détaillés ci-dessus, et dites la réponse à voix haute.

### Collections & concurrence

#### R1. Différence entre `HashMap` et `ConcurrentHashMap`. {#hashmap-concurrenthashmap}
**Réponse :** `HashMap` n'est pas thread-safe : des écritures concurrentes peuvent perdre des mises à jour, corrompre les buckets ou (avant Java 8) boucler indéfiniment au redimensionnement.

`ConcurrentHashMap` est sûre : CAS plus verrou par bin pour les écritures, lectures sans verrou, pas de clé ni valeur `null`, itérateurs faiblement cohérents, opérations composées atomiques (`computeIfAbsent`, `merge`).

Elle ne rend pas atomique une séquence *check-then-act* faite en plusieurs appels.

#### R2. Votre `HashMap` est accédée par plusieurs threads. Quels problèmes peuvent survenir, et comment les corriger ? {#hashmap-accessed-multiple-threads-problems}
**Réponse :** Mises à jour perdues, lectures obsolètes (pas de happens-before), structure corrompue au redimensionnement, `ConcurrentModificationException`, `size()` incohérent.

Corrections, dans l'ordre : éviter le partage (confinement à un thread ou immuabilité), `ConcurrentHashMap` avec des méthodes atomiques, ou un verrou explicite quand plusieurs opérations doivent être atomiques ensemble.

`Collections.synchronizedMap` en dernier recours : l'itération exige encore un verrou manuel.

#### R3. L'application a une race condition qui provoque des paiements en double. Comment l'identifier et la résoudre ? {#application-has-race-condition-causing}
**Réponse :** Identifier : reproduire avec un test concurrent, chercher un check-then-act (`if (!paid) pay()`), comparer logs et lignes en base par clé de paiement/idempotence. Résoudre côté données, pas avec un verrou JVM (inefficace avec plusieurs instances) : **contrainte d'unicité** sur la clé d'idempotence, en-tête d'idempotency key, `SELECT … FOR UPDATE` ou `@Version` optimiste, et machine à états (`PENDING → PAID`) avec un `UPDATE … WHERE status='PENDING'` conditionnel.

#### R4. Plusieurs threads mettent à jour le même enregistrement. Comment garantir la cohérence ? {#multiple-threads-update-same-record}
**Réponse :** En mémoire : `AtomicXxx`/`LongAdder`, `synchronized`/`ReentrantLock` ou `ConcurrentHashMap.compute`. En base : **verrouillage optimiste** (`@Version`, nouvel essai en cas de conflit) quand les conflits sont rares, **pessimiste** (`FOR UPDATE`) quand ils sont fréquents ou que les essais coûtent cher, ou un `UPDATE … SET x = x + 1` atomique. Entre instances, seule la base (ou un verrou distribué) fait foi.

### Threads & asynchrone

#### R5. Votre application crée des milliers de threads et le CPU explose. Que faites-vous ? {#application-creates-thousands-threads-cpu}
**Réponse :** Prendre un thread dump (`jcmd <pid> Thread.print`) et un profil pour voir si les threads sont runnable, bloqués ou en attente. La cause est souvent `new Thread`/`newCachedThreadPool` non bornés et le changement de contexte.

Correction : `ThreadPoolExecutor` borné avec file bornée et politique de rejet, dimensionné selon la charge (CPU : ≈ cœurs ; E/S : plus), et **threads virtuels** en Java 21 pour les E/S bloquantes. Ajouter métriques et alertes sur les pools.

#### R6. Différence entre `ExecutorService` et `CompletableFuture`. {#executorservice-completablefuture}
**Réponse :** `ExecutorService` est un pool qui exécute des tâches et renvoie un `Future` simple (`get()` bloquant, pas de composition). `CompletableFuture` est un conteneur de résultat avec une API de composition non bloquante (`thenApply`, `thenCompose`, `allOf`, `exceptionally`). Ils se combinent : `supplyAsync(task, executor)`.

#### R7. `CompletableFuture` crée-t-il son propre pool de threads ? Lequel utilise-t-il par défaut ? {#completablefuture-create-own-thread-pool}
**Réponse :** Pas de pool propre. Les méthodes `*Async` sans executor utilisent `ForkJoinPool.commonPool()` (ou un thread par tâche si le parallélisme du pool commun est 1). Il est partagé avec les streams parallèles et dimensionné pour le CPU : y faire des E/S bloquantes affame tout. Toujours passer un executor dédié pour les appels bloquants.

#### R8. Une API REST prend 30 secondes car elle appelle trois services. Comment l'optimiser ? {#rest-api-takes-30-seconds}
**Réponse :** Mesurer d'abord (traçage : quel appel domine ?).

Si les appels sont indépendants, les lancer **en parallèle** (`CompletableFuture.allOf` avec executor dédié, ou concurrence structurée/threads virtuels) : la latence devient le *max* et non la *somme*.

Puis : timeouts par appel, cache des données stables, endpoints en lot au lieu de N appels, circuit breaker avec repli, ou passage en asynchrone (202 + polling/webhook) si le travail est intrinsèquement long.

### Mémoire & chaînes

#### R9. Expliquez la gestion mémoire de Java et les différentes zones mémoire de la JVM. {#java-memory-management-different-jvm}
**Réponse :** **Heap** (young : eden + survivors ; old ; géré par le GC), **Metaspace** (métadonnées de classes, mémoire native), **piles de threads** (frames, variables locales), **registre PC** (par thread), **pile des méthodes natives**, plus buffers directs et code cache hors heap. Les objets vivent sur le heap ; références et primitifs dans les frames ; le GC récupère les objets inaccessibles.

#### R10. Qu'est-ce que le registre PC ? {#pc-register}
**Réponse :** Une petite zone par thread qui contient l'adresse de l'instruction JVM en cours (indéfinie pendant une méthode native). C'est ce qui permet à un thread de reprendre après un changement de contexte.

#### R11. Expliquez String Pool vs mémoire Heap. {#string-pool-heap-memory}
**Réponse :** Le string pool (chaînes internées) fait partie du heap depuis Java 7. Les littéraux et les chaînes `intern()` y sont partagés ; `new String(...)` crée un objet distinct sur le heap, hors du pool sauf s'il est interné.

#### R12. Que se passe-t-il avec `new String("hello")` si "hello" existe déjà dans le String Pool ? {#happens-new-string-hello-hello}
**Réponse :** Le littéral `"hello"` reste dans le pool, et `new` alloue quand même un **second objet distinct** sur le heap avec les mêmes caractères. Donc `"hello" == new String("hello")` vaut `false`, et deux objets existent. `.intern()` renvoie celui du pool.

#### R13. Différence entre `==` et `.equals()` pour `String`. {#equals-string}
**Réponse :** `==` compare les références (même objet ?), `.equals()` compare le contenu. Les littéraux peuvent être `==` car poolés, ce qui cache le bug dans les tests. Toujours `.equals()` (ou `Objects.equals` pour la gestion du null).

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q22. Qu'est-ce qu'une race condition, un deadlock et une famine de threads, et comment reconnaître et prévenir chacun ?
2. Q12. Comment le pattern matching pour `switch` se combine-t-il avec les sealed types, et pourquoi est-ce important pour l'exhaustivité ?
3. Q3. Quel est le contrat `equals`/`hashCode`, et que se passe-t-il si on n'en redéfinit qu'un ?
4. Q20. Qu'est-ce qui cause `ConcurrentModificationException`, et quelle est la bonne correction ?
5. Q25. Qu'est-ce que la « safe publication » dans le Java Memory Model, et pourquoi un autre thread peut-il voir un objet à moitié construit ?
6. Q40. Comment profiler un service Java lent ou gourmand en CPU en production ?
7. Q34. Quand choisiriez-vous des virtual threads plutôt qu'une stack réactive (WebFlux) pour un service I/O-bound à forte concurrence, et inversement ?
8. Q38. Quelle est la différence entre `StackOverflowError` et `OutOfMemoryError`, et d'où vient réellement chacune ?
9. S1. Un service de production lève `OutOfMemoryError: Java heap space` après un pic de trafic
10. S22. Le service se bloque au démarrage environ un déploiement sur vingt, sans erreur et sans usage CPU

## 📌 Cheat-sheet

### Collections et égalité

*À retenir d'abord :* (1) redéfinir `equals()` et `hashCode()` ensemble ; (2) ne jamais comparer des objets avec `==` ; (3) ne jamais retirer d'une liste pendant qu'on la parcourt ; (4) utiliser des clés immuables dans les maps.

- **Bucket de `HashMap`** — un emplacement qui contient les entrées dont les clés ont le même hash. Dès qu'un bucket a plus de 8 entrées et que la table a au moins 64 buckets, Java transforme la chaîne en arbre ; retour en liste sous 6 entrées. *Un mauvais `hashCode()` dégrade O(1) vers O(log n).*
- **Contrat `equals()`/`hashCode()`** — deux objets égaux doivent renvoyer le même hash. *Si on le rompt, la map *duplique* silencieusement les clés, ce qui est pire que lent.*
- **Clés de hash mutables** — si un champ utilisé dans `hashCode()` change après l'insertion, l'entrée se retrouve dans le mauvais bucket. *`contains`/`remove` ne la trouvent plus et elle fuit ; indexer sur des ids ou records immuables.*
- **`ConcurrentModificationException`** — levée par les itérateurs *fail-fast* (ils vérifient un compteur de modifications, `modCount`, à chaque pas) quand la collection change pendant la boucle. *Correction : `Iterator.remove()` ou `removeIf`, pas un remove manuel pendant l'itération ni un contournement par index.*

  ```java
  list.removeIf(x -> x.isExpired());   // sûr
  ```

- **Cache d'`Integer`** — Java réutilise les objets `Integer` de -128 à 127 (c'est *spécifié*, pas une coïncidence). *`==` « marche » par contrat dans cette plage, casse (aussi par contrat) en dehors ; toujours utiliser `.equals()` ou unboxer.*
- **`Optional`** — un conteneur pour « peut-être pas de valeur ». *À utiliser uniquement comme type de retour, pas pour un champ ni un paramètre.*
- **`Optional.orElse` vs `orElseGet`** — `orElse(x)` évalue toujours `x` (eager) ; `orElseGet(() -> x)` seulement si vide (lazy). *`get()` ne fait que déplacer l'exception : préférer `orElseThrow`, `map` ou `flatMap`.*
- **Streams** — un pipeline lazy (rien ne s'exécute avant une opération *terminale* comme `collect`) et à usage unique. *Ne jamais muter d'état partagé depuis `parallel().forEach`.*
- **`Stream.toList()` vs `Collectors.toMap`** — `toList()` renvoie une liste non modifiable. *`toMap` lève une exception sur des clés dupliquées sans merge function.*

### Design patterns et fonctionnalités du langage

*À retenir d'abord :* (1) préférer un `enum` pour un singleton ; (2) attraper des exceptions précises, jamais un `catch (Exception e) {}` vide ; (3) utiliser try-with-resources pour tout ce qui se ferme.

- **Singleton, classé du meilleur au pire** — `enum` (bloque aussi les attaques par réflexion/désérialisation) ≈ static holder de Bill Pugh (une classe interne statique privée qui porte l'instance ; le meilleur quand ce ne peut pas être un enum) > double-checked locking avec `volatile` > accesseur `synchronized` > `static final` eager.
- **try-with-resources** — ferme automatiquement les ressources, dans l'ordre inverse de l'ouverture. *Si le bloc try et `close()` lèvent tous deux, l'exception du try l'emporte et celle de `close()` est rattachée comme « suppressed » ; un `finally` écrit à la main perd souvent silencieusement l'une des deux.*
- **Exceptions checked vs unchecked** — checked = conditions récupérables que le compilateur impose de gérer ; unchecked = erreurs de programmation. *`catch (Exception e) {}` est l'anti-pattern que ces deux conceptions cherchent à empêcher.*
- **Type erasure** — les generics sont effacés à la compilation, la JVM ne voit plus `List<String>`. *Ça casse la surcharge par paramètre générique, la création de tableau générique et `instanceof ParameterizedType` ; le compilateur rafistole le polymorphisme avec des bridge methods synthétiques.* *(avancé)*
- **Sealed + pattern matching de `switch`** — le compilateur vérifie que tous les cas sont couverts (exhaustivité). *Ajouter une branche `default` défensive jette cette garantie.*
- **Argent** — jamais `double`. Construire `BigDecimal` depuis une `String` ou `valueOf`. *Comparer avec `compareTo`, pas `equals` (qui compare aussi le scale : `2.0` vs `2.00`).*
- **`BigDecimal.divide` et arrondi** — `divide` exige un scale ou un `MathContext`. *Le mode d'arrondi (`HALF_EVEN` vs `HALF_UP`) et le point d'arrondi sont des règles métier, pas des détails techniques.*
- **`SimpleDateFormat`/`DecimalFormat` partagé** — non thread-safe. *Sous charge, la sortie est corrompue ; utiliser les formatters immuables de `java.time`.*
- **DST (heure d'été/hiver)** — `LocalDateTime` n'a pas de fuseau, donc les gaps et overlaps cassent les planifications en heure murale. *Stocker un `Instant`, calculer les planifications locales avec `ZonedDateTime`, injecter une `Clock` pour les tests.*

### Concurrence

*À retenir d'abord :* (1) `volatile` = visibilité, pas atomicité ; (2) `synchronized` = lock + visibilité ; (3) ne pas bloquer le common pool ; (4) borner les files des pools de threads.

- **`synchronized`** — exclusion mutuelle (un seul thread à la fois) plus une arête *happens-before* : tout ce qui est écrit avant le relâchement du lock est visible du thread suivant qui le prend.
- **`volatile`** — garantit que les autres threads voient la dernière valeur, rien de plus. *Pas d'atomicité pour les opérations composées comme `i++` (lecture-modification-écriture).*
- **Safe publication** — transmettre correctement un objet à un autre thread. *Sans happens-before, l'autre thread peut voir la référence mais des valeurs de champs par défaut (`0`/`null`). Utiliser `volatile`, `final`, init statique ou locks, et ne jamais laisser fuiter `this` depuis un constructeur.*
- **Piège du common pool** — `parallelStream()` et les `CompletableFuture` async par défaut partagent un unique pool à l'échelle de la JVM, `ForkJoinPool.commonPool()`. *Un appel bloquant dans l'un ou l'autre peut affamer du code sans rapport ailleurs dans le processus.*
- **`thenCompose` vs `thenApply`** — `thenApply` transforme une valeur ; `thenCompose` enchaîne une étape qui retourne elle-même un `CompletableFuture`. *Utiliser `thenApply` à cet endroit donne un future imbriqué par erreur.*
- **File d'executor non bornée** (`newFixedThreadPool`) — la file grandit sans limite, donc pas de back-pressure (aucun signal pour ralentir les appelants). *La latence grimpe pendant des minutes, puis OOM (`OutOfMemoryError`) ; utiliser un `ThreadPoolExecutor` borné + politique de rejet + timeouts.*
- **Virtual threads** — des threads bon marché gérés par la JVM, démontés de leur carrier thread (thread OS) pendant un I/O bloquant. *Pièges : `synchronized` autour d'I/O épingle le carrier thread ; une habitude de `ThreadLocal` inoffensive avec les platform threads ne l'est pas à l'échelle des virtual threads.*
- **`ThreadLocal` vs `ScopedValue`** — `ThreadLocal` est mutable et sans portée (fuit sur les threads poolés, lourd avec les virtual threads). *`ScopedValue` (final en JDK 25) est immuable, borné et nettoyé automatiquement.*
- **`ReentrantLock`/`StampedLock`** — à choisir pour les timeouts de `tryLock`, l'interruptibilité, plusieurs `Condition`s ou les lectures optimistes. *Toujours `unlock()` dans `finally` ; `StampedLock` n'est pas réentrant. Le pinning de virtual threads par `synchronized` a été en grande partie supprimé dans JDK 24.* *(avancé)*
- **Deadlock d'initialisation de classe** — des static initializers cycliques entre threads se bloquent dans `<clinit>` (la méthode d'initialisation de classe), souvent invisibles au détecteur de deadlock. *Un initialiseur en échec empoisonne la classe (`NoClassDefFoundError` ensuite) : lire la *première* erreur.* *(avancé)*

### Mémoire, GC et JVM

*À retenir d'abord :* (1) le GC libère ce qui est *inaccessible*, pas ce qui est inutilisé ; (2) `StackOverflowError` = récursion trop profonde, `OutOfMemoryError` = mémoire épuisée dans une région ; (3) un conteneur peut être OOMKilled même avec un heap sain.

- **GC roots** — les points de départ que le GC suit pour trouver les objets vivants : locales de stack, champs statiques, références JNI (code natif). *Il se base sur l'accessibilité, pas sur le comptage de références : les cycles ne sont pas des fuites.*
- **Fuite malgré le GC** — accessibilité involontaire. *Causes typiques : collections statiques, listeners non retirés, `ThreadLocal` non vidé sur des threads poolés (pire à l'échelle des virtual threads).*
- **`StackOverflowError`** — la région stack est pleine, en général à cause d'une récursion non bornée.
- **`OutOfMemoryError`** — région heap, metaspace ou native-thread épuisée : lire le message après les deux-points. *Relever `-Xmx`/`-Xss` (taille max du heap / de la stack d'un thread) retarde, sans le corriger, un algorithme réellement non borné.*
- **Collectors** — G1 = défaut sûr, objectif de pause ajustable. ZGC/Shenandoah = concurrents, pauses sub-ms plates quelle que soit la taille du heap, avec un certain coût CPU/débit. *Choisir selon le SLO (objectif) de latence réel du service, pas selon la réputation.*
- **OOMKilled avec un heap sain** — le coupable est la mémoire native (direct buffers, Metaspace, stacks de threads). *Budgéter heap + non-heap dans la limite du conteneur et inspecter avec NMT (Native Memory Tracking) : `jcmd VM.native_memory`.*
- **Native image vs JVM** — Native Image compile à l'avance sous une hypothèse de monde fermé : le code mort est supprimé, les classes sont initialisées au build, ni JIT/interpréteur/Metaspace à l'exécution. *Gains : démarrage en dizaines de ms, RSS plusieurs fois plus faible. Coûts : débit maximal inférieur (utiliser la PGO), builds longs, réflexion/proxies à déclarer, outillage plus faible. À choisir pour serverless/CLI/scale-to-zero ; garder la JVM (plus AppCDS/CRaC) pour les services longue durée limités par le débit.*
- **Race, deadlock, famine** — race = résultat dépendant du timing (lecture-modification-écriture non synchronisée) ; deadlock = des threads s'attendent en cycle sur leurs verrous ; famine = un thread n'obtient jamais son tour. *Prévention : immuabilité, ordre global des verrous, `tryLock` avec timeout, files équitables ; diagnostic des deadlocks avec `jstack`/`jcmd Thread.print`.*
