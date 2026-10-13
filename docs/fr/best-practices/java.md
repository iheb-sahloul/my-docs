# Bonnes pratiques Java

## 🛡️ Null safety & Optional

### N'utilisez pas `Optional` comme champ ou paramètre

`Optional` est fait uniquement pour les types de retour. Il dit à l'appelant : « cette méthode peut ne rien
renvoyer, gère ce cas ».

**Pourquoi c'est une bonne pratique :** `Optional` a été conçu comme un signal de type de retour, pas comme un
conteneur générique. En paramètre, il n'aide pas : l'appelant peut toujours passer `null` au lieu de
`Optional.empty()`, donc vous avez maintenant trois états à gérer (valeur, vide, `null`), et chaque appel devient
plus verbeux avec `Optional.of(...)`. En champ, c'est un objet de plus par instance, il n'est pas `Serializable`
(ce qui casse les entités JPA, les caches et la réplication de session), et la plupart des frameworks ne s'y
attendent pas. Gardez le champ nullable et ne l'enveloppez que dans le getter.

⛔ `void send(Optional<String> cc)`
✅ `void send(String cc)` + une surcharge, ou `@Nullable String cc`

⛔ `private Optional<Address> address;`
✅ `public Optional<Address> getAddress() { return Optional.ofNullable(address); }`

### N'appelez pas `Optional.get()` à l'aveugle

Utilisez `orElseThrow`, `orElse`, `orElseGet`, `map` ou `ifPresent` au lieu de `get()`.

**Pourquoi c'est une bonne pratique :** `get()` sur un `Optional` vide lève `NoSuchElementException`, qui n'est
qu'une `NullPointerException` sous un autre nom : vous avez réintroduit exactement le bug qu'`Optional` devait
éviter. `orElseThrow(() -> new UserNotFoundException(id))` rend le cas « absent » explicite et le transforme en
erreur métier qui porte du contexte et peut être convertie en réponse adaptée (par exemple un 404).

⛔ `userRepository.findById(id).get()`
✅ `userRepository.findById(id).orElseThrow(() -> new UserNotFoundException(id))`

### Renvoyez des collections vides, jamais `null`

Une méthode qui renvoie une collection doit renvoyer une collection vide quand il n'y a rien à renvoyer.

**Pourquoi c'est une bonne pratique :** les appelants peuvent alors itérer, streamer ou appeler `size()`
directement. Renvoyer `null` oblige chaque appelant à ajouter un test de nullité, et celui qui l'oublie plante
avec une NPE, souvent loin de la source et seulement dans le cas « pas de données », qui est le moins testé. Il
n'y a pas d'excuse de performance : `List.of()`, `Set.of()` et `Map.of()` renvoient des instances immuables
partagées, donc rien n'est alloué.

⛔ `return orders.isEmpty() ? null : orders;`
✅ `return List.of();`

### Échouez vite sur `null` aux frontières

Validez les arguments obligatoires là où ils entrent dans votre objet (constructeurs, méthodes publiques) au lieu
de laisser `null` circuler dans le système.

**Pourquoi c'est une bonne pratique :** si un `null` est stocké silencieusement, la NPE apparaît plus tard, dans
une autre méthode ou un autre thread, avec une stack trace qui pointe vers le symptôme et pas vers la cause.
`Objects.requireNonNull(x, "x")` échoue immédiatement, à la ligne qui a reçu la mauvaise valeur, avec le nom du
paramètre dans le message. Cela documente aussi le contrat : le lecteur voit que l'argument est obligatoire.

```java
// ✅
public OrderService(OrderRepository repository) {
    this.repository = Objects.requireNonNull(repository, "repository");
}
```

## 🚨 Exceptions & logging

### N'avalez jamais une exception

Chaque bloc `catch` doit soit traiter l'erreur, soit la relancer (enveloppée si besoin) avec la cause d'origine.

**Pourquoi c'est une bonne pratique :** un `catch` vide transforme un échec en perte de données silencieuse : la
commande n'a pas été enregistrée, mais l'appelant croit que si, et aucun log ne permet de comprendre pourquoi.
Quand vous enveloppez, passez l'exception d'origine comme `cause` pour garder la stack trace racine dans la chaîne
« Caused by: ». Envelopper permet aussi de traduire une exception de bas niveau (`SQLException`) en une exception
qui a du sens pour votre couche, et d'ajouter du contexte utile (l'id).

```java
// ⛔
try { save(order); } catch (Exception e) { }

// ✅ traiter l'erreur, ou l'envelopper et la relancer avec la cause
try { save(order); } catch (SQLException e) {
    throw new OrderPersistenceException("Failed to save order " + order.id(), e);
}
```

### Attrapez des exceptions précises, pas `Exception`

N'attrapez que les exceptions que vous attendez et savez traiter. N'utilisez pas non plus les exceptions pour
contrôler le flux.

**Pourquoi c'est une bonne pratique :** `catch (Exception e)` attrape aussi celles que vous n'aviez pas prévues :
`NullPointerException`, `IllegalStateException`, `ClassCastException`. De vrais bugs se retrouvent cachés derrière
la valeur par défaut, ici un `0`. Attraper le type précis documente quel échec vous traitez et laisse tous les
autres remonter. Utiliser les exceptions pour le flux normal (par exemple pour sortir d'une boucle) est lent,
car créer une exception capture la stack trace, et cache l'intention : le lecteur s'attend à ce qu'un `catch`
signifie « quelque chose s'est mal passé ».

```java
// ⛔
try { return Integer.parseInt(input); } catch (Exception e) { return 0; }

// ✅
try { return Integer.parseInt(input); } catch (NumberFormatException e) { return 0; }
```

### Loggez avec des placeholders et passez l'exception en dernier

Utilisez les placeholders `{}` au lieu de la concaténation, et passez l'exception elle-même comme dernier
argument.

**Pourquoi c'est une bonne pratique :** avec les placeholders, le message n'est construit que si le niveau de log
est actif, donc les appels `debug` dans les chemins critiques ne coûtent presque rien en production. Surtout,
SLF4J affiche la stack trace quand le dernier argument est un `Throwable`. `e.getMessage()` ne logge qu'une
ligne : vous perdez la stack trace, le type de l'exception et toute la chaîne « Caused by: », qui est souvent là
où se trouve la vraie cause. Le message peut même être `null`.

⛔ `log.error("Failed to process order " + orderId + ": " + e.getMessage());`
✅ `log.error("Failed to process order {}", orderId, e);`

## 🔌 Gestion des ressources

### Fermez les ressources avec try-with-resources

Tout ce qui implémente `AutoCloseable` (streams, connexions JDBC, statements, result sets, clients HTTP) doit
être ouvert dans un bloc `try (...)`.

**Pourquoi c'est une bonne pratique :** un `close()` manuel est sauté dès qu'une exception est levée avant lui.
Chaque fuite garde un descripteur de fichier ou une connexion du pool, jusqu'à ce que le pool soit épuisé et que
l'application se bloque. Un bloc `finally` corrige ça mais il est verbeux et facile à rater (tests de nullité,
un `close()` qui lève lui-même une exception et masque l'erreur d'origine). Try-with-resources ferme sur tous
les chemins, dans l'ordre inverse de l'ouverture, et garde les exceptions levées par `close()` comme exceptions
*supprimées* attachées à l'exception d'origine : rien n'est perdu.

```java
// ⛔ fuite du stream si read() lève une exception
InputStream in = Files.newInputStream(path);
in.read();
in.close();

// ✅
try (InputStream in = Files.newInputStream(path)) {
    in.read();
}
```

## 🧱 Conception d'objets & immuabilité

### Préférez les records pour les value objects

Utilisez un `record` pour les classes qui ne font que porter des données et sont définies par leurs valeurs
(montants, coordonnées, DTO, identifiants).

**Pourquoi c'est une bonne pratique :** les records vous donnent `equals`, `hashCode` et `toString` gratuitement,
générés à partir des composants, donc ils ne peuvent jamais se désynchroniser quand quelqu'un ajoute un champ et
oublie de mettre à jour l'une des méthodes. Ils sont aussi superficiellement immuables (champs `final`, pas de
setters), ce qui élimine toute une catégorie de bugs. La validation tient toujours dans un constructeur compact.
Résultat : une ligne au lieu de ~50 lignes de boilerplate qu'il faudrait aussi maintenir.

⛔ une classe avec un `equals` écrit à la main et pas de `hashCode`
✅ `record Money(BigDecimal amount, Currency currency) {}`

### Préférez l'immuabilité

Rendez les champs `final`, n'exposez pas de setters, et faites des copies défensives des entrées et sorties
mutables.

**Pourquoi c'est une bonne pratique :** un objet immuable peut être partagé entre threads sans verrou, puisqu'il
n'y a rien sur quoi entrer en concurrence. On peut l'utiliser sans risque comme clé de `HashMap` ou dans un
`HashSet`, et le mettre en cache et le réutiliser. Il est aussi plus simple à comprendre : une fois construit et
valide, il reste valide, donc vous n'avez pas besoin de savoir qui d'autre en garde une référence. Sans copie
défensive, l'appelant garde une référence vers la liste et peut modifier votre objet de l'extérieur, en
contournant toute validation. `List.copyOf` fait une copie non modifiable (et ne recopie pas si la liste l'est
déjà), donc la renvoyer directement est sûr.

```java
// ⛔ l'appelant peut modifier la liste interne
public Order(List<Line> lines) { this.lines = lines; }
public List<Line> lines() { return lines; }

// ✅
public Order(List<Line> lines) { this.lines = List.copyOf(lines); }
public List<Line> lines() { return lines; }
```

### Redéfinissez `equals` et `hashCode` ensemble

Si deux objets sont `equals`, ils doivent avoir le même `hashCode`.

**Pourquoi c'est une bonne pratique :** les collections à base de hash utilisent d'abord `hashCode` pour trouver
le bucket, puis `equals` à l'intérieur. Si vous ne redéfinissez que `equals`, deux objets « égaux » atterrissent
dans des buckets différents : `set.contains(x)` renvoie `false` et `HashSet` stocke des doublons. Rien ne lève
d'exception, c'est juste faux en silence. N'utilisez jamais de champs mutables dans ces méthodes : si une clé
change après son insertion, son hash change, la map cherche dans le mauvais bucket et l'entrée est perdue
(toujours en mémoire, mais inaccessible). Solution la plus simple : utilisez un record.

### Préférez les factories statiques ou les builders aux constructeurs télescopiques

Quand un constructeur a plus de 3–4 paramètres, ou plusieurs du même type, utilisez un builder ou des méthodes
factory statiques nommées (`Money.of(...)`, `Duration.ofSeconds(...)`).

**Pourquoi c'est une bonne pratique :** `new Pizza("L", true, false, true, null)` est illisible sans ouvrir la
classe, et inverser deux `boolean` compile très bien mais est un bug. Un builder nomme chaque argument, rend les
arguments optionnels vraiment optionnels, et peut valider tout l'objet dans `build()`. Les factories statiques
ont un nom qui explique l'intention, peuvent renvoyer des instances en cache ou un sous-type, et évitent d'avoir
dix surcharges de constructeur.

⛔ `new Pizza("L", true, false, true, null)`
✅ `Pizza.builder().size("L").cheese(true).ham(true).build()`

### Préférez la composition à l'héritage

Réutilisez du comportement en gardant une instance d'une autre classe et en lui déléguant les appels, plutôt
qu'en l'étendant.

**Pourquoi c'est une bonne pratique :** l'héritage vous couple aux détails d'implémentation du parent, pas
seulement à son API (le problème de la « classe de base fragile »). Dans l'exemple, `HashSet.addAll()` appelle
`add()` en interne, donc redéfinir les deux compte chaque élément deux fois, et cela casserait à nouveau si un
futur JDK changeait ce comportement interne. La sous-classe hérite aussi de toutes les méthodes publiques, y
compris celles qui contournent votre logique. Avec la composition, vous n'exposez que ce que vous voulez, vous
contrôlez chaque appel, et vous pouvez changer le délégué (par exemple pour un `TreeSet`).

L'héritage reste pertinent pour une vraie relation « est-un », à l'intérieur d'un même package ou module, ou
quand la classe parente est conçue et documentée pour être étendue (classes abstraites, template methods).

```java
// ⛔ hérite de toutes les méthodes de HashSet, et addAll() appelle add() en interne : double comptage
class CountingSet<E> extends HashSet<E> { ... }

// ✅ envelopper et déléguer
class CountingSet<E> {
    private final Set<E> delegate = new HashSet<>();
    private int added;

    boolean add(E e) { added++; return delegate.add(e); }
}
```

### Déclarez avec des interfaces, pas des implémentations

Utilisez l'interface (`List`, `Map`, `Set`) comme type des variables, champs, paramètres et types de retour.
N'utilisez la classe concrète qu'après `new`.

**Pourquoi c'est une bonne pratique :** le code dépend alors de *ce que* fait l'objet, pas de *comment* il le
fait. Vous pouvez passer d'`ArrayList` à `LinkedList`, ou de `HashMap` à `LinkedHashMap`, en changeant une seule
ligne. Les appelants peuvent aussi passer n'importe quelle implémentation (`List.of(...)`, `Arrays.asList(...)`,
une collection Hibernate) au lieu d'être forcés de convertir. Renvoyer `ArrayList` depuis une méthode publique
fait de l'implémentation une partie de votre API, et vous ne pourrez plus la changer sans casser les appelants.

⛔ `ArrayList<Order> orders = new ArrayList<>();`
✅ `List<Order> orders = new ArrayList<>();`

### Utilisez des enums plutôt que des constantes int / String

Représentez un ensemble fixe de valeurs avec un `enum`.

**Pourquoi c'est une bonne pratique :** avec des constantes `int` ou `String`, le compilateur accepte n'importe
quelle valeur : `update(42)` compile, et une faute de frappe comme `"PIAD"` aussi. Un enum restreint le paramètre
aux valeurs valides dès la compilation. Vous obtenez aussi un `toString()` lisible dans les logs, des expressions
`switch` dont le compilateur vérifie qu'aucun cas ne manque, et `EnumMap` / `EnumSet`, plus rapides et plus
compacts que leurs équivalents à base de hash. Les enums peuvent aussi porter des champs et du comportement
(`Status.PAID.isFinal()`), ce qui garde la logique associée au même endroit.

```java
// ⛔
static final int STATUS_PAID = 1;
void update(int status) { ... }       // accepte 42

// ✅ typé, utilisable dans un switch, compatible EnumMap / EnumSet
enum Status { PENDING, PAID, REFUNDED }
void update(Status status) { ... }
```

## 🧰 Bibliothèque standard : le bon type pour le bon usage

### Utilisez `BigDecimal` pour l'argent

N'utilisez jamais `double` ou `float` pour des montants qui doivent être exacts.

**Pourquoi c'est une bonne pratique :** `double` est un nombre à virgule flottante binaire, et la plupart des
fractions décimales (0,1, 0,2) n'ont pas de représentation binaire exacte. De petites erreurs apparaissent et
s'accumulent sur des milliers d'opérations, et un total faux d'un centime est un vrai bug comptable. `BigDecimal`
stocke la valeur décimale exacte. Il a pourtant ses propres pièges :

- `new BigDecimal(0.1)` prend le `double` déjà faux, donc construisez-le à partir d'une `String` ou avec
  `BigDecimal.valueOf(double)` (qui passe par `Double.toString`).
- Fixez toujours l'échelle et le `RoundingMode` explicitement. `HALF_EVEN` (« arrondi du banquier ») évite un biais
  systématique quand on arrondit beaucoup de valeurs.
- `equals` compare aussi l'échelle, donc `0.10` et `0.1` ne sont pas égaux. Utilisez `compareTo` pour comparer
  des valeurs.

```java
// ⛔
double total = 0.1 + 0.2;                   // 0.30000000000000004
new BigDecimal(0.1);                        // 0.1000000000000000055511151231257827...

// ✅
BigDecimal total = new BigDecimal("0.10").add(BigDecimal.valueOf(0.2));
total = total.setScale(2, RoundingMode.HALF_EVEN);

// ⛔ equals compare l'échelle : 0.10 != 0.1
a.equals(b)
// ✅
a.compareTo(b) == 0
```

### Utilisez `java.time`, pas `Date` / `Calendar`

Utilisez l'API `java.time` (Java 8+). Stockez des `Instant` (UTC), et ne convertissez en `ZonedDateTime` que pour
l'affichage.

**Pourquoi c'est une bonne pratique :** `Date` et `Calendar` sont mutables (quiconque en garde une référence peut
changer la valeur), ont des API déroutantes (mois qui commencent à 0, années décalées de 1900), et
`SimpleDateFormat` n'est pas thread-safe : le partager dans un champ `static` donne des dates corrompues sous
charge. Les types `java.time` sont immuables et thread-safe, et chaque type dit ce qu'il représente : `Instant`
est un point dans le temps, `LocalDate` une date sans fuseau horaire, `ZonedDateTime` une date et une heure dans
une région, `Duration` une durée. Stocker en UTC évite les bugs de changement d'heure et la confusion entre
serveurs dans des fuseaux différents. Le fuseau de l'utilisateur est une question d'affichage.

⛔ `new Date()`, `Calendar.getInstance()`, `SimpleDateFormat` (pas thread-safe)
✅ `Instant.now()`, `DateTimeFormatter.ISO_INSTANT`

### Utilisez `StringBuilder` dans les boucles

Ne concaténez pas des chaînes avec `+` dans une boucle.

**Pourquoi c'est une bonne pratique :** `String` est immuable, donc chaque `+=` alloue une nouvelle chaîne et
recopie tout ce qui a été construit jusque-là. Pour n éléments, cela fait O(n²) copies et beaucoup de déchets
pour le GC. Le compilateur optimise `+` dans une même expression, mais pas d'une itération à l'autre.
`StringBuilder` ajoute dans un seul buffer qui grandit, en O(n). Pour le cas simple « joindre avec un
séparateur », `String.join` ou `Collectors.joining` est plus clair et évite aussi le bug de la virgule finale.

```java
// ⛔ crée une nouvelle String à chaque itération
String csv = "";
for (String name : names) csv += name + ",";

// ✅ ou simplement String.join(",", names)
StringBuilder csv = new StringBuilder();
for (String name : names) csv.append(name).append(',');
```

## 🌊 Streams & style fonctionnel

### Pas d'effets de bord dans les opérations de stream

Les opérations de stream (`map`, `filter`, `forEach`...) ne doivent pas modifier d'état externe. Construisez le
résultat avec une opération terminale (`toList()`, `collect`, `reduce`).

**Pourquoi c'est une bonne pratique :** un stream décrit *quel* résultat vous voulez, et le pipeline décide
comment le calculer. Ajouter dans une `ArrayList` externe depuis `forEach` fonctionne par chance : passez en
`.parallel()` et cela devient une data race (éléments perdus, `ArrayIndexOutOfBoundsException`), car `ArrayList`
n'est pas thread-safe. C'est aussi plus difficile à lire : le lecteur doit trouver la liste mutable pour comprendre
ce que produit le stream. `.toList()` (Java 16+) renvoie une liste non modifiable, sûre par défaut.

```java
// ⛔
List<String> result = new ArrayList<>();
orders.stream().filter(Order::isPaid).forEach(o -> result.add(o.id()));

// ✅
List<String> result = orders.stream().filter(Order::isPaid).map(Order::id).toList();
```

## 🧵 Concurrence

### Ne gérez pas les threads à la main

Utilisez un `ExecutorService` (ou les virtual threads à partir de Java 21) au lieu de `new Thread()`, et des
collections concurrentes au lieu des wrappers `synchronized`.

**Pourquoi c'est une bonne pratique :** chaque `new Thread()` est un thread OS coûteux, sans limite, sans
réutilisation, sans gestion du cycle de vie et sans moyen de récupérer un résultat ou une exception. Sous charge,
cela donne un épuisement de la mémoire ou des milliers de threads en concurrence. Un executor limite la
concurrence, réutilise les threads, renvoie des `Future`, et peut être arrêté proprement. Les virtual threads
(`Executors.newVirtualThreadPerTaskExecutor()`) rendent « un thread par tâche » peu coûteux pour les I/O
bloquantes.

`Collections.synchronizedMap` verrouille toute la map à chaque appel, et les actions composées comme « `get`, puis
`put` » restent en concurrence, car deux threads peuvent lire la même ancienne valeur. `ConcurrentHashMap` utilise
un verrouillage fin et propose des opérations composées atomiques comme `merge`, `compute` et `putIfAbsent`.

⛔ `new Thread(task).start();`, `Collections.synchronizedMap(new HashMap<>())`
✅ `ExecutorService` / virtual threads, `ConcurrentHashMap`

```java
// ✅ vérification-puis-action atomique
counts.merge(key, 1, Integer::sum);
```

### Nettoyez toujours les `ThreadLocal`

Appelez `remove()` dans un bloc `finally` une fois la requête ou la tâche terminée.

**Pourquoi c'est une bonne pratique :** les conteneurs de servlets et les executors réutilisent des threads d'un
pool. Une valeur laissée dans un `ThreadLocal` reste sur le thread et est visible par la *requête suivante* qu'il
traite. Avec un id de tenant ou un contexte de sécurité, cela veut dire que la requête d'un utilisateur peut
s'exécuter avec les données ou les droits d'un autre. Cela fuit aussi de la mémoire : la valeur (et, dans les
serveurs d'applications, tout le classloader de l'application) ne peut pas être collectée tant que le thread est
vivant, ce qui provoque des `OutOfMemoryError` après des redéploiements. `finally` garantit que le nettoyage
s'exécute même si le traitement lève une exception.

```java
// ✅
CURRENT_TENANT.set(tenant);
try {
    handle(request);
} finally {
    CURRENT_TENANT.remove();
}
```

### Arrêtez toujours les executors

Un `ExecutorService` que vous créez doit être arrêté. À partir de Java 19, ouvrez-le dans un bloc
try-with-resources.

**Pourquoi c'est une bonne pratique :** les threads d'un pool créé avec `Executors.newFixedThreadPool` ne sont pas
des threads démons. Si personne n'appelle `shutdown()`, ils gardent la JVM en vie après la fin de `main`, et dans
une application qui tourne longtemps, chaque executor oublié est un groupe de threads inactifs qui ne disparaît
jamais. Depuis Java 19, `ExecutorService` est `AutoCloseable` : `close()` refuse les nouvelles tâches et attend la
fin de celles déjà soumises, donc le bloc ne se termine que quand le travail est fini.

```java
// ⛔ fuite de threads, la JVM peut ne jamais s'arrêter
ExecutorService pool = Executors.newFixedThreadPool(4);
pool.submit(task);

// ✅ attend les tâches, puis arrête le pool
try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
    pool.submit(task);
}
```

### Donnez un executor à `CompletableFuture` et gérez ses erreurs

Passez votre propre executor aux méthodes `*Async`, et terminez la chaîne par `exceptionally` ou `handle`.

**Pourquoi c'est une bonne pratique :** sans executor, `supplyAsync` s'exécute sur le
`ForkJoinPool.commonPool()` partagé, dimensionné pour du travail CPU (nombre de cœurs moins un). Des I/O
bloquantes dessus affament tous les autres utilisateurs du pool, y compris les parallel streams. Et une exception
dans une étape asynchrone n'apparaît nulle part tant que personne n'appelle `join()` ou n'ajoute de handler :
l'échec est stocké dans le future puis silencieusement ignoré.

```java
// ⛔ bloque le common pool, les erreurs disparaissent
CompletableFuture.supplyAsync(() -> client.fetch(id)).thenAccept(this::save);

// ✅
CompletableFuture.supplyAsync(() -> client.fetch(id), ioExecutor)
        .thenAccept(this::save)
        .exceptionally(e -> { log.error("Fetch failed for {}", id, e); return null; });
```

### Utilisez les atomiques pour un état partagé simple

Pour un compteur ou un flag partagé, utilisez `AtomicInteger`, `AtomicLong`, `LongAdder` ou `AtomicBoolean`.
N'utilisez `volatile` que pour une valeur unique écrite par un thread et lue par d'autres.

**Pourquoi c'est une bonne pratique :** `count++` fait trois opérations (lire, ajouter, écrire). Deux threads
peuvent lire la même valeur et écrire tous les deux `n + 1`, et un incrément est perdu. `volatile` ne corrige pas
ça : il garantit la visibilité, pas l'atomicité. Les atomiques font le lire-modifier-écrire en une seule
instruction CPU (compare-and-swap), sans verrou. `LongAdder` est encore plus rapide quand beaucoup de threads
mettent à jour le même compteur, comme des métriques de requêtes.

⛔ `private volatile int count; ... count++;`
✅ `private final AtomicInteger count = new AtomicInteger(); ... count.incrementAndGet();`

### Prenez toujours les verrous dans le même ordre

Quand du code a besoin de plusieurs verrous, tous les threads doivent les prendre dans le même ordre global.

**Pourquoi c'est une bonne pratique :** si le thread A verrouille `from` puis `to`, et que le thread B fait un
transfert dans l'autre sens et verrouille `to` puis `from`, chacun finit par tenir le verrou que l'autre attend.
C'est un deadlock : les deux threads bloquent pour toujours, sans exception ni log. Ordonner les verrous selon une
clé stable (un id) rend le cycle impossible. `tryLock` avec un timeout est la solution de repli quand il n'existe
pas d'ordre naturel.

```java
// ⛔ transfer(a, b) et transfer(b, a) en même temps peuvent provoquer un deadlock
synchronized (from) { synchronized (to) { move(from, to, amount); } }

// ✅ toujours verrouiller le plus petit id en premier
Account first = from.id() < to.id() ? from : to;
Account second = first == from ? to : from;
synchronized (first) { synchronized (second) { move(from, to, amount); } }
```

### Ne bloquez pas de virtual threads dans un `synchronized` (avant Java 24)

En Java 21–23, utilisez un `ReentrantLock` au lieu de `synchronized` autour des appels bloquants exécutés par des
virtual threads.

**Pourquoi c'est une bonne pratique :** un virtual thread est peu coûteux parce qu'il est détaché de son thread
porteur (OS) quand il bloque. Avant Java 24 (JEP 491), un virtual thread qui bloque en tenant un moniteur est
*épinglé* (pinned) : le porteur ne peut pas être réutilisé. Il n'y a qu'autant de porteurs que de cœurs CPU, donc
quelques threads épinglés qui font des I/O lentes figent toute l'application. `ReentrantLock` n'épingle pas.
Lancez avec `-Djdk.tracePinnedThreads=full` pour détecter l'épinglage.

```java
// ⛔ épingle le thread porteur pendant l'appel HTTP (Java 21–23)
synchronized (this) { response = httpClient.send(request, ofString()); }

// ✅
lock.lock();
try { response = httpClient.send(request, ofString()); } finally { lock.unlock(); }
```

## 🧬 Génériques & collections

### N'utilisez jamais de types bruts

Donnez toujours son paramètre à un type générique : `List<String>`, pas `List`. Utilisez `List<?>` quand le type
n'a pas d'importance.

**Pourquoi c'est une bonne pratique :** un type brut (raw type) désactive la vérification des génériques. Le
compilateur vous laisse ajouter un `Integer` dans ce qui est en réalité une liste de `String`, avec un simple
warning. L'erreur apparaît plus tard sous forme de `ClassCastException` dans le code qui lit la liste, loin de la
ligne fautive. Les types bruts n'existent que pour la compatibilité avec le code d'avant Java 5.

```java
// ⛔ compile, puis lève ClassCastException à la lecture
List names = new ArrayList<String>();
names.add(42);
String first = (String) names.get(0);

// ✅
List<String> names = new ArrayList<>();
```

### Utilisez des wildcards bornés dans les API (PECS)

« Producer `extends`, consumer `super` » : utilisez `? extends T` pour un paramètre dans lequel vous lisez,
`? super T` pour un paramètre dans lequel vous écrivez.

**Pourquoi c'est une bonne pratique :** les génériques sont invariants : une `List<Integer>` n'est *pas* une
`List<Number>`. Une méthode qui prend une `List<Number>` refuse une `List<Integer>` alors qu'elle ne fait qu'y lire
des nombres. Les wildcards permettent à l'API d'accepter tous les types qui fonctionnent, sans cast.
`Collections.copy(List<? super T> dest, List<? extends T> src)` est l'exemple de référence.

⛔ `double sum(List<Number> numbers)` — refuse `List<Integer>`
✅ `double sum(List<? extends Number> numbers)`

### Choisissez la bonne collection

Utilisez `ArrayList` par défaut, `ArrayDeque` pour les piles et les files, `EnumMap` / `EnumSet` pour les clés
enum, et `LinkedHashMap` quand l'ordre d'itération compte.

**Pourquoi c'est une bonne pratique :** `Stack` et `Vector` sont des classes historiques qui synchronisent chaque
appel pour rien. `LinkedList` semble intéressante pour les insertions sur le papier, mais chaque nœud est un objet
séparé : elle consomme beaucoup plus de mémoire, rate le cache CPU à chaque étape, et `get(i)` est en O(n).
`ArrayDeque` est plus rapide en pile comme en file. L'ordre d'itération d'une `HashMap` n'est pas spécifié et
peut changer d'une version du JDK à l'autre, donc les tests qui en dépendent cassent au hasard.

⛔ `Stack<Task> stack = new Stack<>();`, `new LinkedList<>()` comme liste par défaut
✅ `Deque<Task> stack = new ArrayDeque<>();`, `new ArrayList<>()`

### Ne modifiez pas une collection pendant que vous l'itérez

Utilisez `removeIf`, un `Iterator.remove()` explicite, ou construisez une nouvelle collection.

**Pourquoi c'est une bonne pratique :** supprimer d'une `ArrayList` dans une boucle for-each lève une
`ConcurrentModificationException`, ou pire, quand l'élément supprimé est l'avant-dernier, saute silencieusement le
dernier : la boucle s'arrête plus tôt et aucune erreur n'est levée. `removeIf` le fait en une passe, correctement,
et exprime l'intention.

```java
// ⛔ ConcurrentModificationException, ou un élément sauté
for (Order o : orders) if (o.isCancelled()) orders.remove(o);

// ✅
orders.removeIf(Order::isCancelled);
```

### Sachez que `List.of` et ses cousins sont immuables et refusent `null`

`List.of`, `Set.of`, `Map.of`, `List.copyOf` et `Stream.toList()` renvoient des collections non modifiables.
`List.of` et `copyOf` lèvent aussi une exception sur les éléments `null`.

**Pourquoi c'est une bonne pratique :** appeler `add` dessus lève `UnsupportedOperationException` à l'exécution,
pas à la compilation, car elles implémentent l'interface `List` normale. C'est souvent ce que vous voulez, mais une
méthode qui en reçoit une et essaie de la modifier plantera en production. `Arrays.asList` est un autre piège :
sa taille est fixe, donc `set` fonctionne mais `add` lève une exception. Quand un appelant doit modifier le
résultat, renvoyez `new ArrayList<>(...)` et dites-le.

⛔ `List<String> tags = List.of("a"); tags.add("b");` — `UnsupportedOperationException`
✅ `List<String> tags = new ArrayList<>(List.of("a")); tags.add("b");`

## ✨ Java moderne

### N'utilisez `var` que quand le type est évident

Utilisez `var` quand la partie droite montre déjà le type (`new`, une factory, un cast). Écrivez le type sinon.

**Pourquoi c'est une bonne pratique :** `var` supprime du bruit comme `Map<String, List<Order>> map = new
HashMap<>()`. Mais avec `var result = service.process(input);`, le lecteur doit ouvrir un autre fichier pour
savoir ce qu'est `result`, et les code reviews se font sans IDE. `var` infère aussi le type concret :
`var list = new ArrayList<String>()` est une `ArrayList`, pas une `List`.

⛔ `var result = service.process(input);`
✅ `var orders = new ArrayList<Order>();`, `Order order = service.process(input);`

### Préférez les switch expressions

Utilisez `switch` comme expression avec des flèches (`->`), pas l'ancienne instruction avec `break`.

**Pourquoi c'est une bonne pratique :** l'ancien `switch` passe au cas suivant quand vous oubliez un `break`
(fall-through), un bug classique. La forme avec flèche ne fait jamais de fall-through. En tant qu'expression, elle
doit produire une valeur pour chaque entrée : avec un enum ou un type scellé, le compilateur vérifie que tous les
cas sont couverts, donc ajouter une constante à l'enum casse le build au lieu de tomber silencieusement dans un
`default`.

```java
// ⛔ oublier un break fait passer au cas suivant
String label;
switch (status) {
    case PAID: label = "Paid"; break;
    case PENDING: label = "Pending";
    default: label = "Unknown";
}

// ✅ exhaustif, pas besoin de default pour un enum
String label = switch (status) {
    case PENDING -> "Pending";
    case PAID -> "Paid";
    case REFUNDED -> "Refunded";
};
```

### Utilisez le pattern matching plutôt que des casts

Utilisez `instanceof` avec une variable liée, et les record patterns pour décomposer un record.

**Pourquoi c'est une bonne pratique :** `if (o instanceof Order) { Order order = (Order) o; ... }` répète le
type, et une erreur de copier-coller entre le test et le cast compile très bien et plante à l'exécution. Le
pattern matching teste et caste en une seule étape, et la variable n'existe que là où le test a réussi.

⛔ `if (shape instanceof Circle) { double r = ((Circle) shape).radius(); }`
✅ `if (shape instanceof Circle c) { double r = c.radius(); }`
✅ `if (shape instanceof Circle(double r)) { ... }`

### Utilisez des types scellés pour les hiérarchies fermées

Quand un type a un ensemble fixe de sous-types (moyens de paiement, événements, résultats), déclarez-le `sealed` et
listez-les avec `permits`.

**Pourquoi c'est une bonne pratique :** une interface scellée dit au compilateur (et au lecteur) qu'aucune autre
implémentation n'existe. Combinée aux records et au pattern matching dans un `switch`, vous obtenez une
vérification d'exhaustivité : ajoutez un sous-type, et chaque `switch` qui ne le traite pas cesse de compiler. Avec
une interface ouverte, il faudrait une branche `default` qui lève une exception, et vous ne découvririez le cas
manquant qu'en production.

```java
// ✅
sealed interface Payment permits Card, Transfer {}
record Card(String number) implements Payment {}
record Transfer(String iban) implements Payment {}

String describe(Payment p) {
    return switch (p) {
        case Card c -> "Card " + c.number();
        case Transfer t -> "Transfer " + t.iban();
    };
}
```

### Utilisez les text blocks pour les chaînes multi-lignes

Écrivez le SQL, le JSON et les autres chaînes multi-lignes sous forme de text blocks `"""`.

**Pourquoi c'est une bonne pratique :** des lignes concaténées avec `"\n" +` et des guillemets échappés sont
difficiles à lire et faciles à casser : un espace manquant entre deux lignes de SQL donne `FROM ordersWHERE`. Un
text block garde le texte tel qu'il apparaît, gère l'indentation, et n'a pas besoin d'échapper `"`. Utilisez
`formatted(...)` pour les valeurs, mais jamais pour les paramètres SQL : ceux-là passent par des paramètres liés.

```java
// ⛔
String json = "{\n" + "  \"name\": \"" + name + "\"\n" + "}";

// ✅
String json = """
        {
          "name": "%s"
        }
        """.formatted(name);
```

## 🚀 Native image & démarrage

### Choisissez l'image native pour le démarrage et l'empreinte, pas pour la vitesse

Construisez une image native GraalVM quand la charge est limitée par le démarrage ou la mémoire (serverless, CLI,
scale-to-zero, nombreuses petites instances). Gardez la JVM pour les services longue durée limités par le débit.

**Pourquoi c'est une bonne pratique :** une image native démarre en dizaines de millisecondes et consomme une fraction de
la mémoire, car le JIT, les métadonnées de classes et le profilage ont disparu et le code mort a été supprimé au build.
Le prix : un débit maximal inférieur à un JIT C2 chaud, des builds longs et un runtime en monde fermé. Essayez d'abord
AppCDS, CRaC ou SnapStart : ils apportent souvent l'essentiel du gain au démarrage sans ces contraintes. Comparez
toujours les deux artefacts sous votre propre charge.

⛔ Passer au natif « parce que c'est plus rapide » pour une API très sollicitée qui tourne des semaines
✅ Natif pour une Lambda ou une CLI avec un problème de cold start ; JVM + AppCDS pour l'API longue durée

### Écrivez du code compatible AOT : évitez la réflexion à l'exécution et le scan du classpath

Préférez l'injection par constructeur et une configuration explicite à `Class.forName`, à la réflexion calculée et au
scan de classpath maison. Quand la réflexion est inévitable, déclarez-la avec `@RegisterReflectionForBinding` ou un
`RuntimeHintsRegistrar`.

**Pourquoi c'est une bonne pratique :** le compilateur natif ne garde que ce qu'il peut prouver atteignable au build.
Tout ce qui est retrouvé par son nom à l'exécution est supprimé silencieusement et échoue plus tard avec
`NoSuchMethodException` ou un corps JSON vide, souvent sur un chemin rarement utilisé. Des hints explicites en font
une décision de build que l'on peut relire et tester.

⛔ `Class.forName(config.get("handler")).getDeclaredConstructor().newInstance()`
✅ `Map<String, Handler> handlers` injectée par Spring, plus un hint pour tout DTO lu par réflexion

### Exécutez aussi les tests en mode natif

Lancez `mvn -PnativeTest test` (ou `./gradlew nativeTest`) et un smoke test sur le binaire construit en CI, pas seulement
la suite de tests JVM.

**Pourquoi c'est une bonne pratique :** du code peut passer tous les tests JVM et casser dans l'image, car les
métadonnées de réflexion ou de ressources manquantes n'apparaissent qu'à l'exécution de l'exécutable compilé. Les builds
natifs sont lents : exécutez-les sur main et les branches de release et utilisez `-Ob` (build rapide) ailleurs.

### Utilisez la PGO et le bon GC quand le débit natif compte

Si une image native doit aussi soutenir un débit élevé, construisez avec l'optimisation guidée par profil
(`--pgo-instrument`, charge représentative, rebuild avec `--pgo=default.iprof`) et envisagez `--gc=G1` sur Oracle
GraalVM pour de plus gros heaps.

**Pourquoi c'est une bonne pratique :** par défaut l'image est compilée sans profils d'exécution et utilise le Serial GC,
c'est ce que l'on sacrifie par rapport à C2 et G1. La PGO restaure une grande partie de l'optimisation et un collecteur
parallèle évite de longues pauses stop-the-world ; les deux demandent un benchmark sur votre propre charge pour se
justifier.

## 🧭 Conception du code & des API

### Injectez les dépendances et l'horloge

Recevez les collaborateurs, et une `Clock` quand le temps compte, en paramètres du constructeur au lieu de les
créer dans la classe ou d'appeler des méthodes statiques.

**Pourquoi c'est une bonne pratique :** une classe qui appelle `new EmailClient()` ou `Instant.now()` ne peut pas
être testée sans envoyer de vrais emails ou attendre le bon moment. Avec la dépendance injectée, un test passe un
fake, et avec une `Clock`, il passe `Clock.fixed(...)` et vérifie « expire dans 30 jours » de façon
déterministe. Cela rend aussi les dépendances visibles dans le constructeur : un constructeur avec 8 paramètres
signale une classe qui en fait trop.

```java
// ⛔ intestable : dépend de l'heure réelle
boolean isExpired() { return Instant.now().isAfter(expiresAt); }

// ✅
boolean isExpired(Clock clock) { return Instant.now(clock).isAfter(expiresAt); }
```

### Gardez la visibilité la plus réduite possible

Rendez les classes et membres `private` ou package-private par défaut, et `public` seulement quand un autre
package en a besoin.

**Pourquoi c'est une bonne pratique :** tout ce qui est `public` fait partie de votre API : quelqu'un va
l'appeler, et vous ne pourrez plus le changer sans le casser. Les classes package-private peuvent être refactorées
librement. Cela garde aussi chaque package cohérent : si seul le service est public, personne ne peut appeler le
repository directement et contourner votre validation. Les tests dans le même package ont toujours accès au code
package-private.

⛔ `public class OrderMapper` utilisée uniquement par `OrderService` dans le même package
✅ `class OrderMapper`

### Exceptions unchecked pour les bugs, exceptions métier pour les erreurs métier

Levez `IllegalArgumentException` / `IllegalStateException` pour les erreurs de programmation. Créez des exceptions
précises (`InsufficientFundsException`) pour les règles métier auxquelles l'appelant peut réagir.

**Pourquoi c'est une bonne pratique :** les exceptions checked obligent chaque appelant de la pile à les déclarer
ou à les attraper, et dans les lambdas elles ne se composent pas du tout, donc on finit par les envelopper ou les
avaler. La plupart des erreurs ne peuvent de toute façon pas être traitées localement et doivent remonter jusqu'à
un handler global. Une exception métier nommée dit ce qui s'est mal passé, peut porter des données (le compte, le
montant manquant), et peut être convertie en un statut HTTP précis. Une `RuntimeException("error")` générique ne
le peut pas.

⛔ `throw new RuntimeException("Not enough money");`
✅ `throw new InsufficientFundsException(accountId, missing);`

### Gardez des méthodes courtes qui font une seule chose

Une méthode doit faire une seule chose, à un seul niveau d'abstraction. Extrayez une méthode nommée quand un bloc a
besoin d'un commentaire pour être compris.

**Pourquoi c'est une bonne pratique :** une méthode de 200 lignes mélange validation, règles métier, persistance
et formatage, donc on ne peut pas tester une partie sans les autres, et chaque modification risque de casser une
partie sans rapport. De petites méthodes bien nommées se lisent comme les étapes de l'algorithme. Le nom remplace
le commentaire, et contrairement à un commentaire, il ne peut pas devenir obsolète sans que personne ne le
remarque.

```java
// ⛔
void checkout(Cart cart) {
    // valider
    ... 30 lignes ...
    // calculer le total
    ... 20 lignes ...
}

// ✅
void checkout(Cart cart) {
    validate(cart);
    Money total = computeTotal(cart);
    charge(cart.customer(), total);
}
```

### Nommez les choses selon ce qu'elles signifient

Utilisez des noms qui disent ce qu'est une valeur dans le domaine, pas son type. Évitez les abréviations et les
noms génériques comme `data`, `info`, `manager`, `tmp`.

**Pourquoi c'est une bonne pratique :** le code est lu bien plus souvent qu'il n'est écrit. `List<Order> list` ne
dit rien que le type ne dise déjà ; `unpaidOrders` dit ce qu'elle contient et pourquoi elle existe. Les booléens
se lisent mieux comme des questions (`isActive`, `hasDiscount`). Les unités ont leur place dans le nom ou le
type : `timeout` est ambigu, `timeoutMs` ou une `Duration` ne l'est pas.

⛔ `int d; // temps écoulé en jours`, `List<Order> list`, `long timeout`
✅ `int elapsedDays`, `List<Order> unpaidOrders`, `Duration timeout`
