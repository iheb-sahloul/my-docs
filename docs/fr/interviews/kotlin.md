# Kotlin pour développeurs Java

Kotlin côté backend (Spring Boot, coroutines), tel qu'on le demande à un senior venant de Java. Les internes de la JVM (GC, modèle mémoire, threads) sont dans [Java Core & JVM](java-core-jvm.md#interface-abstract-class) ; Spring lui-même dans [Spring & Architecture](spring-architecture.md#dependency-injection-spring-advantages).

## 🟢 Fondamentaux

#### Q1. Comment fonctionne la null safety de Kotlin, et qu'est-ce qu'un type plateforme ? {#kotlin-null-safety-platform-type}
**Réponse :** La nullabilité fait partie du type : `String` ne peut jamais être null, `String?` peut l'être. Le compilateur oblige à traiter `String?` avec l'appel sûr `?.`, l'opérateur Elvis `?:`, un smart cast après `if (x != null)`, ou `!!` (affirme non-null, lève `NullPointerException`). Les valeurs venant de Java ont des **types plateforme** (`String!`) : Kotlin ne sait pas si elles peuvent être null, il vous laisse donc les traiter dans un sens ou dans l'autre et la vérification se fait à l'exécution. Annotez le côté Java (`@Nullable`/`@NonNull`, JSpecify) ou déclarez explicitement le type Kotlin à la frontière.

**Exemple :**

```kotlin
fun greeting(name: String?): String =
    "Hello, ${name?.trim()?.ifEmpty { null } ?: "patient"}"

val header: String? = request.getHeader("X-Request-Id")   // API Java : déclarer String? explicitement
val id = header ?: UUID.randomUUID().toString()
```

#### Q2. Quand utiliser une `data class`, une classe/interface `sealed` et une `value class` ? {#data-class-sealed-class-interface}
**Réponse :** Une **data class** porte des valeurs : le compilateur génère `equals`/`hashCode`/`toString`/`copy`/`componentN` à partir des propriétés du constructeur primaire (l'équivalent Kotlin d'un `record` Java, avec `copy` en plus). Une hiérarchie **sealed** est un ensemble fermé de sous-types connu à la compilation, donc un `when` dessus est exhaustif sans `else`, idéal pour les états et résultats du domaine. Une **value class** (`@JvmInline value class`) enveloppe une valeur dans un type distinct, sans allocation dans la plupart des cas : `PatientId` et `PractitionerId` ne peuvent plus être inversés par erreur.

**Exemple :**

```kotlin
@JvmInline value class PractitionerId(val value: Long)

sealed interface BookingResult {
    data class Booked(val appointmentId: Long) : BookingResult
    data object SlotTaken : BookingResult
    data class Rejected(val reason: String) : BookingResult
}

fun toHttp(r: BookingResult) = when (r) {            // exhaustif : ajouter un sous-type casse la compilation ici
    is BookingResult.Booked -> 201
    BookingResult.SlotTaken -> 409
    is BookingResult.Rejected -> 422
}
```

#### Q3. Que sont les fonctions d'extension, et quelles sont leurs limites ? {#extension-functions-limits}
**Réponse :** Une fonction d'extension `fun Type.name()` ajoute une méthode à un type existant sans héritage. Elle compile en méthode statique qui reçoit le receveur en premier paramètre. Elle est donc **résolue statiquement** (sur le type déclaré, pas le type à l'exécution), n'accède pas aux membres `private` et ne peut pas redéfinir une fonction membre : un membre de même signature gagne toujours. Utilisez les extensions pour de petits helpers locaux et du mapping (`Entity.toDto()`), pas pour cacher de la logique métier dans des fichiers au hasard.

**Exemple :**

```kotlin
fun AppointmentEntity.toDto() = AppointmentDto(id = id, startsAt = startsAt, practitioner = practitionerName)

open class Shape; class Circle : Shape()
fun Shape.name() = "shape"
fun Circle.name() = "circle"
val s: Shape = Circle()
s.name()   // "shape" : résolu sur le type déclaré
```

#### Q4. Comment choisir entre `let`, `apply`, `also`, `run` et `with` ? {#let-apply-also-run}
**Réponse :** Elles diffèrent sur deux points : comment l'objet est référencé à l'intérieur (`it` ou `this`) et ce qu'elles renvoient (le résultat du lambda ou l'objet lui-même). `let` (it → résultat) : transformer une valeur nullable, `x?.let { … }`. `apply` (this → objet) : configurer un objet en construction. `also` (it → objet) : un effet de bord comme un log sans casser une chaîne. `run` (this → résultat) et `with(x)` (this → résultat) : calculer quelque chose à partir des membres d'un objet. Choisissez d'après la valeur de retour, et évitez de les imbriquer : trois scope functions imbriquées sont illisibles.

**Exemple :**

```kotlin
val client = HttpClient.newBuilder().apply { connectTimeout(Duration.ofSeconds(2)) }.build()
val email = patient.email?.let { it.lowercase().trim() }
repository.save(appointment).also { log.info("booked {}", it.id) }
```

#### Q5. Collections ou séquences : quand `asSequence()` vaut-il le coup ? {#collections-sequences-assequence-worth}
**Réponse :** Les opérateurs de collections Kotlin (`map`, `filter`) sont **eager** : chaque étape crée une liste intermédiaire complète. Une `Sequence` est **paresseuse** et traite les éléments un par un à travers toute la chaîne, en s'arrêtant tôt avec `first`/`take`. Utilisez les séquences pour de longues chaînes sur de grosses collections ou quand vous court-circuitez. Pour de petites listes, les collections eager sont plus simples et souvent plus rapides. C'est la même idée que les streams Java, sans le parallélisme.

**Exemple :**

```kotlin
val firstFree = slots.asSequence()
    .filter { it.start > now }
    .filterNot { it in booked }
    .firstOrNull()          // s'arrête au premier résultat, sans listes intermédiaires
```

## 🟡 Pièges seniors

#### Q6. Que sont les coroutines et la concurrence structurée, et comment se comparent-elles aux virtual threads ? {#coroutines-structured-concurrency-compare-virtual}
**Réponse :** Une coroutine est un calcul qui peut se **suspendre** (sur un appel `suspend`) sans bloquer son thread, puis reprendre plus tard, éventuellement sur un autre thread. La **concurrence structurée** signifie que chaque coroutine tourne dans un `CoroutineScope` : un parent attend ses enfants, un enfant en échec annule ses frères et son parent (sauf sous `supervisorScope`), et annuler le scope annule tout, donc rien ne fuit. `coroutineScope { async {…}; async {…} }` est le fan-out standard. Les virtual threads de Java 21 donnent aussi une concurrence bon marché en style bloquant, mais sans annulation structurée intégrée (`StructuredTaskScope` est encore en preview). Les coroutines apportent en plus `Flow`, l'annulation et des dispatchers explicites. Dans une app Spring MVC sur Java 21, les virtual threads suffisent souvent. Les coroutines brillent avec WebFlux ou quand il faut paralléliser de nombreux appels concurrents.

**Exemple :**

```kotlin
suspend fun practitionerPage(id: PractitionerId): Page = coroutineScope {
    val profile = async { profileClient.get(id) }
    val slots = async { availabilityClient.next(id, days = 7) }
    Page(profile.await(), slots.await())     // si l'un échoue, l'autre est annulé
}
```

**Pourquoi c'est un piège :** `GlobalScope.launch` (ou un `CoroutineScope(Job())` maison que personne n'annule) casse la concurrence structurée : le travail survit à la requête, ses erreurs sont perdues et il fuit sous charge.

#### Q7. À quoi servent les dispatchers, et comment appeler du code bloquant depuis une coroutine ? {#dispatchers-call-blocking-code-coroutine}
**Réponse :** Un dispatcher décide quels threads exécutent une coroutine : `Dispatchers.Default` (travail CPU, environ un thread par cœur), `Dispatchers.IO` (I/O bloquantes, pool élastique plus grand, 64 threads par défaut), `Dispatchers.Main` (UI uniquement). Une fonction `suspend` n'est pas automatiquement non bloquante : si elle appelle JDBC, `Thread.sleep` ou un client HTTP bloquant, elle bloque son thread. Enveloppez les appels bloquants dans `withContext(Dispatchers.IO) { … }`, et utilisez `limitedParallelism(n)` pour plafonner la concurrence face à une petite ressource comme un pool de 10 connexions.

**Exemple :**

```kotlin
private val db = Dispatchers.IO.limitedParallelism(10)   // aligné sur la taille du pool Hikari

suspend fun findAppointments(id: PractitionerId): List<Appointment> =
    withContext(db) { jdbcTemplate.query(SQL, mapper, id.value) }
```

**Pourquoi c'est un piège :** bloquer dans `Dispatchers.Default` affame toutes les autres coroutines (il n'existe que quelques threads). Le débit s'effondre sous charge alors que le CPU semble inactif. Voir [S1](kotlin.md#after-moving-endpoint-coroutines-throughput).

#### Q8. Comment fonctionne l'annulation des coroutines, et quels sont les pièges (`runBlocking`, `catch (e: Exception)`) ? {#coroutine-cancellation-traps-runblocking-catch}
**Réponse :** L'annulation est **coopérative** : une coroutine annulée lève `CancellationException` à son prochain point de suspension (`delay`, `yield`, un appel suspendant). Une boucle CPU sans suspension doit vérifier `isActive` ou appeler `ensureActive()`. Trois pièges : (1) `catch (e: Exception)` attrape aussi `CancellationException` et avale l'annulation, donc relancez-la ou attrapez des exceptions plus précises ; (2) un nettoyage dans `finally` qui doit suspendre doit tourner dans `withContext(NonCancellable)` ; (3) `runBlocking` bloque le thread appelant, il est donc réservé à `main` et aux tests, jamais dans un thread de requête ou une autre coroutine (risque de deadlock sur un petit pool). Utilisez `withTimeout` pour borner les appels distants.

**Exemple :**

```kotlin
try {
    withTimeout(2.seconds) { smsGateway.send(reminder) }
} catch (e: CancellationException) {
    throw e                                  // ne jamais avaler l'annulation (TimeoutCancellationException en est une)
} catch (e: IOException) {
    log.warn("sms failed, will retry", e)
}
```

**Pourquoi c'est un piège :** un `catch (e: Exception)` générique autour d'un appel suspendant fait disparaître silencieusement timeouts et annulations de requête. La coroutine continue de tourner après le départ du client.

#### Q9. Que faut-il savoir pour utiliser Kotlin avec Spring Boot et JPA ? {#need-know-kotlin-spring-boot}
**Réponse :** Spring crée des proxys de classes (`@Transactional`, `@Configuration`), mais les classes Kotlin sont `final` par défaut. Le plugin de compilation **`kotlin-spring`** (all-open) ouvre les classes annotées avec des stéréotypes Spring. JPA exige un constructeur sans argument et des entités non finales : utilisez **`kotlin-jpa`** (no-arg) plus all-open pour `@Entity`. Ajoutez **`jackson-module-kotlin`** pour que Jackson comprenne constructeurs, valeurs par défaut et nullabilité. Préférez l'injection par constructeur (`class S(private val repo: Repo)`), `@ConfigurationProperties` sur une data class, et le support coroutines de Spring (méthodes de contrôleur `suspend`, `CoroutineCrudRepository` avec R2DBC). Ne modélisez **pas** les entités JPA en data classes : `equals`/`hashCode` générés sur tous les champs cassent avec le lazy loading, les ids mutables et les `Set`, et `toString` peut déclencher des chargements lazy ou une récursion.

**Exemple :**

```kotlin
// build.gradle.kts
plugins { kotlin("plugin.spring"); kotlin("plugin.jpa") }

@Entity
class Appointment(
    @Id @GeneratedValue var id: Long? = null,
    var startsAt: Instant,
    @ManyToOne(fetch = FetchType.LAZY) var practitioner: Practitioner,
) {
    override fun equals(other: Any?) = other is Appointment && id != null && id == other.id
    override fun hashCode() = javaClass.hashCode()
}
```

**Pourquoi c'est un piège :** sans le plugin all-open, `@Transactional` sur une classe ou méthode finale est silencieusement ignoré (aucun proxy ne peut être généré). Le code compile et tourne, mais sans transaction.

#### Q10. Qu'est-ce qui casse à la frontière Java/Kotlin ? {#breaks-java-kotlin-boundary}
**Réponse :** (1) Les **types plateforme** venant de Java peuvent être null à l'exécution même si vous les avez utilisés comme non-null (voir [Q1](kotlin.md#kotlin-null-safety-platform-type)). (2) Kotlin n'a pas d'exceptions vérifiées, donc les appelants Java d'une fonction Kotlin qui lève `IOException` ont besoin de `@Throws(IOException::class)` pour pouvoir l'attraper. (3) Les arguments par défaut sont invisibles depuis Java sans `@JvmOverloads`. (4) Les membres d'un `companion object` ont besoin de `@JvmStatic` (méthodes) ou `@JvmField`/`const` (champs) pour paraître statiques depuis Java. (5) Les fonctions de premier niveau deviennent `FileNameKt.fn()` sauf avec `@file:JvmName`. (6) La `List` Kotlin est en lecture seule, pas immuable : Java peut encore la modifier si l'instance est une `ArrayList`. (7) Les fonctions `suspend` prennent un paramètre `Continuation` supplémentaire et ne s'appellent pas directement depuis Java ; exposez un `CompletableFuture` avec `future { }`.

**Exemple :**

```kotlin
class SlotService {
    @JvmOverloads
    fun next(practitionerId: Long, days: Int = 7, durationMin: Int = 20): List<Slot> = TODO()

    companion object {
        @JvmStatic fun create() = SlotService()
        const val MAX_DAYS = 28
    }
}
```

**Pourquoi c'est un piège :** dans une base mixte qui migre depuis Java, la plupart des NPE Kotlin viennent d'API Java non annotées. Les équipes pensent « Kotlin n'a pas de NPE » et retirent les vérifications précisément à la frontière qui en a besoin.

## 🔴 Expert / Ouvert

#### Q11. `Flow`, fonctions `suspend` ou Reactor : comment choisir pour un backend asynchrone ? {#flow-suspend-functions-reactor-async}
**Réponse :** Une fonction `suspend` renvoie **une** valeur de façon asynchrone. Un `Flow` est un flux asynchrone **froid** de plusieurs valeurs, avec backpressure par suspension. Les opérateurs sont séquentiels et le code se lit de façon impérative (`map`, `filter`, `buffer`, `flowOn`). `StateFlow`/`SharedFlow` sont chauds, pour l'état et la diffusion. Les `Mono`/`Flux` de Reactor couvrent les mêmes besoins avec une API d'opérateurs plus large, mais stack traces et débogage sont plus difficiles. Avec Spring WebFlux, les coroutines Kotlin sont une alternative de premier plan (`kotlinx-coroutines-reactor` fait le pont : `awaitSingle()`, `asFlow()`). Décision : Spring MVC simple (avec virtual threads) si le service fait surtout du CRUD sur JDBC ; coroutines quand il faut beaucoup d'appels distants concurrents ou du streaming ; Reactor seulement là où une bibliothèque l'impose. Ne mélangez pas types réactifs et coroutines partout dans le même service.

**Exemple :**

```kotlin
@GetMapping("/practitioners/{id}/slots", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun liveSlots(@PathVariable id: Long): Flow<Slot> =
    slotEvents.asFlow()                                   // Flux -> Flow
        .filter { it.practitionerId == id }
        .map { it.toSlot() }
```

**Pourquoi c'est un piège :** choisir WebFlux et les coroutines « pour la performance » sur un service dont le goulot est un pool JDBC bloquant. Vous ajoutez de la complexité sans gain tant que l'accès base n'est pas non bloquant (R2DBC) ou isolé sur `Dispatchers.IO`.

#### Q12. Quand utiliser `inline`/`reified`, la délégation de classe et les délégués de propriété ? {#inline-reified-class-delegation-property}
**Réponse :** **`inline`** copie le corps d'une fonction d'ordre supérieur et ses lambdas au point d'appel. Cela supprime l'allocation des lambdas et permet les paramètres de type **`reified`** (le type est connu à l'exécution, donc `T::class` fonctionne sans argument `Class<T>`), ainsi que le `return` non local. Réservez-le aux petits helpers génériques, car il fait grossir le bytecode. La **délégation de classe** (`class A(b: B) : B by b`) implémente une interface en déléguant à une instance : de la composition sans boilerplate, utile pour des décorateurs comme le cache ou les métriques. **Délégués de propriété** : `by lazy` (initialisation paresseuse thread-safe par défaut), `Delegates.observable`, `by map`. La question porte sur la retenue : ces outils sont utiles quand ils suppriment de la répétition, nuisibles quand ils cachent le flot de contrôle.

**Exemple :**

```kotlin
inline fun <reified T> ObjectMapper.read(json: String): T = readValue(json, T::class.java)
val dto = mapper.read<AppointmentDto>(body)

class CachedAvailability(private val delegate: AvailabilityPort) : AvailabilityPort by delegate {
    private val cache = ConcurrentHashMap<Long, List<Slot>>()
    override fun next(id: Long) = cache.getOrPut(id) { delegate.next(id) }   // le reste est délégué
}
```

**Pourquoi c'est un piège :** marquer de grosses fonctions `inline` « pour la performance » fait grossir le bytecode à chaque point d'appel sans gain mesurable. Le bénéfice n'existe que pour les lambdas et `reified`.

#### Q13. Comment tester du code coroutines et Kotlin Spring ? {#test-coroutine-kotlin-spring-code}
**Réponse :** Utilisez `kotlinx-coroutines-test` : `runTest { }` exécute un test suspendant sur un `TestScope` avec un **temps virtuel**, donc `delay(10.minutes)` se termine instantanément et `advanceTimeBy`/`advanceUntilIdle` pilotent l'horloge. Injectez les dispatchers (paramètre de constructeur) au lieu de coder `Dispatchers.IO` en dur, pour que le test puisse passer un `StandardTestDispatcher`. Pour un `Flow`, collectez avec `toList()` ou utilisez Turbine (`flow.test { awaitItem() }`). Utilisez **MockK** plutôt que Mockito : il gère les classes `final`, `coEvery`/`coVerify` pour les fonctions suspendantes et le mock d'`object`. En intégration, `@SpringBootTest` plus Testcontainers PostgreSQL (`@ServiceConnection`) exactement comme en Java, et `WebTestClient` pour les contrôleurs coroutines.

**Exemple :**

```kotlin
class ReminderServiceTest {
    private val sms = mockk<SmsGateway>(relaxed = true)

    @Test
    fun `sends reminder 24h before the appointment`() = runTest {
        val service = ReminderService(sms, dispatcher = StandardTestDispatcher(testScheduler))
        service.schedule(appointmentAt = currentTime.milliseconds + 25.hours)

        advanceTimeBy(1.hours + 1.seconds)        // temps virtuel : aucune attente réelle
        coVerify(exactly = 1) { sms.send(any()) }
    }
}
```

**Pourquoi c'est un piège :** tester avec `runBlocking` et de vrais `delay` donne des tests lents et instables. Des dispatchers codés en dur rendent l'horloge virtuelle inutile, car le travail s'échappe vers de vrais threads.

## 🎯 Scénarios réels

### S1. Après le passage d'un endpoint aux coroutines, le débit s'effondre sous charge alors que le CPU reste bas {#after-moving-endpoint-coroutines-throughput}
- **Symptômes :** la latence p99 passe de 80 ms à plusieurs secondes sous un trafic modeste, CPU vers 20 %, aucune erreur, et les thread dumps montrent tous les threads `DefaultDispatcher-worker` en `RUNNABLE`/`WAITING` dans des appels JDBC.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une fonction `suspend` appelle directement le repository JDBC bloquant, elle tourne donc sur `Dispatchers.Default`, qui n'a qu'environ un thread par cœur. Quelques requêtes lentes occupent tous les workers et toutes les autres coroutines attendent. Confirmez avec un thread dump (`jcmd <pid> Thread.print`) et l'agent de debug des coroutines (`-Dkotlinx.coroutines.debug`).
- **Résolution :** Enveloppez les appels bloquants dans `withContext(Dispatchers.IO.limitedParallelism(poolSize))`, ou passez à R2DBC pour un chemin réellement non bloquant. Gardez le travail CPU sur `Default`.
- **Prévention :** Règle de revue : une fonction `suspend` ne doit pas appeler d'API bloquante sans changer de contexte. Ajoutez BlockHound dans les tests pour échouer sur les appels bloquants dans des threads non bloquants, et faites un test de charge avant de passer un endpoint aux coroutines.

</details>

### S2. Un service Kotlin lève `NullPointerException` sur une valeur typée non-null {#kotlin-service-throws-nullpointerexception-value}
- **Symptômes :** `NullPointerException: getHeader(...) must not be null` (ou un crash dans le constructeur d'une data class) en production, sur un chemin où tous les types Kotlin sont non-null.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une API Java (en-tête servlet, service legacy, JSON désérialisé par Jackson sans le module Kotlin) a renvoyé `null` dans un type plateforme que le code utilisait comme `String`. Kotlin insère une vérification de nullité à la frontière et échoue là. La stack trace pointe la première ligne Kotlin qui utilise la valeur.
- **Résolution :** Déclarez le type à la frontière comme nullable (`val h: String? = ...`) et traitez le cas absent, enregistrez `jackson-module-kotlin` pour que les champs JSON manquants échouent clairement ou prennent leur valeur par défaut, et annotez le code Java avec `@Nullable`.
- **Prévention :** Traitez chaque appel Java comme une frontière de confiance, activez JSpecify/`-Xjsr305=strict` pour que la nullabilité Java annotée soit appliquée, et ajoutez un test avec le champ ou l'en-tête manquant.

</details>

### S3. `@Transactional` sur un service Kotlin n'a aucun effet, et des écritures partielles arrivent en base {#transactional-ignored-final-class}
- **Symptômes :** Une exception au milieu de `placeOrder()` laisse la commande enregistrée sans ses lignes ; le même code en Java faisait un rollback.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les classes et méthodes Kotlin sont `final` par défaut : le proxy CGLIB de Spring ne peut pas les surcharger et l'annotation est ignorée silencieusement. Vérifiez la présence du plugin `kotlin-spring` (all-open) ; vérifiez aussi l'auto-invocation, qui échoue de la même manière en Java.
- **Exemple :**

  ```kotlin
  plugins {
      kotlin("plugin.spring") version "2.0.21"   // ouvre les classes @Component/@Transactional/...
      kotlin("plugin.jpa") version "2.0.21"      // constructeurs sans argument pour @Entity
  }
  ```

- **Résolution :** Ajoutez le plugin `kotlin-spring` (start.spring.io le fait par défaut), recompilez, et ajoutez un test d'intégration qui lève une exception en cours de route et vérifie que rien n'a été persisté.
- **Prévention :** Générez les projets Kotlin via le Spring initializr, gardez un test de rollback par cas d'usage transactionnel, et une règle ArchUnit/Konsist qui garantit que les services sont proxyables.

</details>

### S4. Une entité JPA écrite en `data class` provoque des doublons dans un `Set`, des `StackOverflowError` dans les logs et des rafales de lazy loading {#data-class-entity-equals-breaks}
- **Symptômes :** Ajouter une entité à un `HashSet` avant puis après le save donne deux éléments ; logger une commande déclenche des dizaines de requêtes SQL et parfois un `StackOverflowError`.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** `data class` génère `equals`/`hashCode`/`toString` sur toutes les propriétés du constructeur : le hash change quand l'ID est assigné, `toString` parcourt les associations lazy (N requêtes) et les relations bidirectionnelles bouclent à l'infini.
- **Exemple :**

  ```kotlin
  @Entity
  class Order(
      @Id @GeneratedValue var id: Long? = null,
      @OneToMany(mappedBy = "order") val lines: MutableList<OrderLine> = mutableListOf(),
  ) {
      override fun equals(other: Any?) = other is Order && id != null && id == other.id
      override fun hashCode() = Order::class.hashCode()
      override fun toString() = "Order(id=$id)"
  }
  ```

- **Résolution :** Utilisez une `class` classique pour les entités avec un `equals` basé sur l'ID, un `hashCode` constant et un `toString` qui ne touche pas aux associations. Gardez `data class` pour les DTO et les value objects.
- **Prévention :** Une règle d'analyse statique (detekt/Konsist) qui interdit `data class` avec `@Entity`, plus le plugin `kotlin-jpa` pour les constructeurs sans argument.

</details>

### S5. Sous charge, un service Spring MVC utilisant des coroutines ne répond plus, tous les threads Tomcat bloqués {#runblocking-in-request-thread}
- **Symptômes :** Un thread dump montre les 200 threads `http-nio` parqués dans `BlockingCoroutine.joinBlocking` ; les health checks expirent et les pods redémarrent.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Quelqu'un a appelé une fonction `suspend` depuis un contrôleur bloquant avec `runBlocking { ... }`. Chaque requête monopolise un thread Tomcat pendant l'attente, et si la coroutine a besoin d'un thread du même pool épuisé (ou si la limite de `Dispatchers.IO` est atteinte), c'est l'interblocage.
- **Exemple :**

  ```kotlin
  // avant : bloque le thread de requête
  @GetMapping("/quote") fun quote() = runBlocking { pricing.fetch() }

  // après : Spring MVC et WebFlux supportent les handlers suspend
  @GetMapping("/quote") suspend fun quote() = pricing.fetch()
  ```

- **Résolution :** Rendez le handler `suspend` (supporté par Spring MVC depuis la 6 et par WebFlux) ou restez entièrement bloquant avec un client classique ; jamais de pont `runBlocking` sur un chemin de requête. En Java 21, les virtual threads sont une alternative plus simple pour du code bloquant.
- **Prévention :** Une règle de lint qui interdit `runBlocking` hors `main` et tests, et un test de charge qui surveille la saturation des pools de threads.

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q1. Comment fonctionne la null safety de Kotlin, et qu'est-ce qu'un type plateforme ?
2. Q2. Quand utiliser une `data class`, une classe/interface `sealed` et une `value class` ?
3. Q4. Comment choisir entre `let`, `apply`, `also`, `run` et `with` ?
4. Q6. Que sont les coroutines et la concurrence structurée, et comment se comparent-elles aux virtual threads ?
5. Q7. À quoi servent les dispatchers, et comment appeler du code bloquant depuis une coroutine ?
6. Q8. Comment fonctionne l'annulation des coroutines, et quels sont les pièges ?
7. Q9. Que faut-il savoir pour utiliser Kotlin avec Spring Boot et JPA ?
8. Q10. Qu'est-ce qui casse à la frontière Java/Kotlin ?
9. Q11. `Flow`, fonctions `suspend` ou Reactor : comment choisir pour un backend asynchrone ?
10. S1. Après le passage d'un endpoint aux coroutines, le débit s'effondre sous charge alors que le CPU reste bas

## 📌 Cheat-sheet

- **Null safety** — `?.`, `?:`, smart casts ; `!!` est un code smell. *Les valeurs Java sont des types plateforme : déclarez-les `T?`.*
- **Types** — `data class` pour les valeurs, `sealed` pour les états fermés (`when` exhaustif), `value class` pour les ids typés. *Jamais de data class comme entité JPA.*
- **Scope functions** — choisir d'après la valeur de retour : `apply`/`also` renvoient l'objet, `let`/`run`/`with` le résultat. *Pas d'imbrication.*
- **Coroutines** — concurrence structurée : `coroutineScope`, `async`/`await`, pas de `GlobalScope`. *`supervisorScope` quand les frères doivent survivre à un échec.*
- **Dispatchers** — `Default` pour le CPU, `IO` pour le bloquant, `limitedParallelism` aligné sur un pool. *Bloquer sur `Default` affame tout.*
- **Annulation** — coopérative ; relancer `CancellationException` ; `withTimeout` sur les appels distants. *`runBlocking` seulement dans `main` et les tests.*
- **Spring** — plugins `kotlin-spring` + `kotlin-jpa`, `jackson-module-kotlin`, injection par constructeur. *Sans all-open, `@Transactional` est silencieusement ignoré.*
- **Interop** — `@JvmOverloads`, `@JvmStatic`, `@Throws`, `@file:JvmName`. *`List` est en lecture seule, pas immuable.*
- **Tests** — `runTest` + temps virtuel, dispatchers injectés, MockK `coEvery`, Turbine pour `Flow`. *Testcontainers comme en Java.*
