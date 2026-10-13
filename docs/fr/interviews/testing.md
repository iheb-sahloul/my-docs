# Tests

Les règles et checklists de revue sont dans [Bonnes pratiques › Tests](../best-practices/testing.md) ; ce module est le Q&A d'entretien.

## 🟢 Fondamentaux

### Stratégie

#### Q1. Qu'est-ce que la pyramide des tests, et est-ce toujours la bonne forme ?

**Réponse :** La pyramide dit : beaucoup de tests unitaires rapides et isolés à la base, moins de tests d'intégration
au milieu, et une poignée de tests end-to-end lents au sommet. La raison est le coût et la vitesse du feedback : un
test unitaire s'exécute en millisecondes et pointe une classe, alors qu'un test end-to-end prend des secondes ou des
minutes, exige un environnement complet, et quand il échoue il dit « quelque chose est cassé quelque part ». La forme
est un repère, pas une loi. Pour un service Spring typique très orienté CRUD, la plupart des bugs se trouvent dans le
SQL, le mapping et le câblage, pas dans la logique métier : un « trophée de tests » avec une couche d'intégration plus
épaisse (vraie base via Testcontainers, vrai HTTP via MockMvc) attrape souvent davantage pour le même effort. La
constante des deux formes : garder peu de tests end-to-end, centrés sur les parcours utilisateur critiques.

**Exemple :**

```text
            /\        E2E : login → checkout → paiement (5–20 tests, minutes)
           /  \
          /----\      Intégration : repository + vrai Postgres, controller + MockMvc (centaines, secondes)
         /      \
        /--------\    Unitaires : règles de prix, validateurs, mappers (milliers, millisecondes)
```

#### Q2. Unitaire, intégration, end-to-end — où placer les frontières ?

**Réponse :** Placez-les selon ce qui est réel et ce qui est remplacé, pas selon l'outil. Un **test unitaire** exerce
une unité de comportement (souvent une classe, parfois un petit groupe) avec toutes les dépendances d'I/O remplacées :
pas de réseau, pas de base, pas de système de fichiers, pas d'horloge. Un **test d'intégration** met au moins une vraie
pièce externe dans la boucle : une vraie base, un vrai broker, le vrai contexte Spring, ou la vraie sérialisation HTTP.
Un **test end-to-end** pilote le système déployé comme le ferait un utilisateur ou un client, via son interface
publique, avec tout de réel. La question utile pour chaque test : « s'il échoue, à combien d'endroits le bug peut-il
se trouver ? » La réponse doit grandir à mesure qu'on monte.

#### Q3. Mock, stub, fake, spy — quelle différence, et quand utiliser chacun ?

**Réponse :** Un **stub** renvoie des réponses préparées pour que le code testé puisse s'exécuter
(`when(repo.findById(1)).thenReturn(...)`) ; on n'assert pas dessus. Un **mock** est configuré avec des attentes et on
**vérifie les interactions** (`verify(mailer).send(...)`) ; à utiliser quand l'interaction *est* le comportement, par
exemple « un email est envoyé ». Un **fake** est une implémentation légère qui fonctionne (repository en mémoire,
horloge factice) ; il donne un comportement réaliste sans infrastructure. Un **spy** enveloppe un vrai objet et
enregistre les appels, en permettant de surcharger certaines méthodes. Règle pratique : préférer les vrais objets,
puis les fakes, puis les stubs ; n'utiliser des mocks que pour les commandes sortantes dont il faut vérifier l'effet.

**Exemple :**

```java
// Stub : fournit des données
when(rates.rateFor("EUR")).thenReturn(new BigDecimal("1.08"));
// Mock : vérifie une commande sortante
verify(notifier).orderConfirmed(orderId);
// Fake : une implémentation en mémoire qui fonctionne
class InMemoryOrderRepository implements OrderRepository {
    private final Map<OrderId, Order> store = new HashMap<>();
    public void save(Order o) { store.put(o.id(), o); }
    public Optional<Order> findById(OrderId id) { return Optional.ofNullable(store.get(id)); }
}
```

#### Q4. Qu'est-ce qui fait un bon test unitaire ?

**Réponse :** Il teste **un comportement**, via l'API publique, et son nom dit lequel (`rejectsOrderWhenStockIsEmpty`,
pas `testProcess2`). Il suit **Arrange–Act–Assert** avec une séparation visible. Il est **F.I.R.S.T.** : rapide,
indépendant (pas de dépendance d'ordre, pas d'état mutable partagé), répétable (pas d'horloge, d'aléatoire ni de
réseau), auto-validant (des assertions, pas de lecture de logs) et écrit au bon moment (avec le code). Et il échoue
pour une seule raison : quand il passe au rouge, le nom et le message d'assertion disent ce qui a cassé sans ouvrir
de debugger.

**Exemple :**

```java
@Test
void appliesTenPercentDiscountAboveThreshold() {
    var order = anOrder().withTotal("120.00").build();      // Arrange

    var price = pricing.finalPrice(order);                   // Act

    assertThat(price).isEqualByComparingTo("108.00");        // Assert
}
```

### Outillage Java

#### Q5. Sur quelles fonctionnalités de JUnit 5 vous appuyez-vous au-delà de `@Test` ?

**Réponse :** `@ParameterizedTest` avec `@CsvSource`/`@MethodSource` pour couvrir un tableau de cas sans tests
copiés-collés ; des classes `@Nested` pour regrouper les cas par contexte (« quand le panier est vide ») ;
`@DisplayName` pour des rapports lisibles ; `assertThrows`/`assertAll` pour les exceptions et les assertions groupées ;
les extensions (`@ExtendWith`) pour Mockito, Spring et Testcontainers ; et `@Tag` pour séparer suites rapides et
lentes dans le build. La plupart des équipes associent JUnit à **AssertJ** pour des assertions fluides et bien
rapportées (`assertThat(list).extracting(Order::status).containsOnly(PAID)`).

**Exemple :**

```java
@ParameterizedTest
@CsvSource({ "99.99, 0", "100.00, 10", "500.00, 50" })
void discountByTotal(BigDecimal total, BigDecimal expectedDiscount) {
    assertThat(pricing.discount(total)).isEqualByComparingTo(expectedDiscount);
}
```

#### Q6. Comment bien utiliser Mockito, et que ne faut-il jamais mocker ?

**Réponse :** Utilisez `@ExtendWith(MockitoExtension.class)` avec `@Mock`/`@InjectMocks`, ne stubbez que ce dont le
test a besoin (les strict stubs signalent les stubs inutilisés), et utilisez `ArgumentCaptor` quand il faut inspecter
ce qui a été passé. Ne mockez pas : **les value objects et DTO** (construisez-les), **la classe testée**, **les types
qui ne vous appartiennent pas** (mocker `RestTemplate` ou `JdbcTemplate` encode vos suppositions sur une bibliothèque ;
enveloppez-la derrière votre propre port et mockez celui-ci, ou testez l'adaptateur contre la vraie chose), et **tout
par défaut**. Un test dont la préparation fait vingt lignes de `when(...)` et dont l'assertion est un `verify(...)`
teste généralement l'implémentation, pas le comportement.

**Exemple :**

```java
@Test
void publishesEventWithOrderTotal() {
    service.confirm(orderId);

    var captor = ArgumentCaptor.forClass(OrderConfirmed.class);
    verify(events).publish(captor.capture());
    assertThat(captor.getValue().total()).isEqualByComparingTo("108.00");
}
```

### Frontend

#### Q7. Quelle est la philosophie de React Testing Library, et comment cibler les éléments ?

**Réponse :** « Plus vos tests ressemblent à la façon dont le logiciel est utilisé, plus ils vous donnent confiance. »
Rendez le composant, interagissez comme un utilisateur (`userEvent.click`, `userEvent.type`), et vérifiez ce que
l'utilisateur voit, pas le state ni les méthodes internes. Ciblez dans cet ordre : `getByRole` (avec un nom
accessible), `getByLabelText`, `getByText`, et seulement ensuite `getByTestId`. Cibler par rôle sert aussi de contrôle
d'accessibilité : si vous ne trouvez pas le bouton par rôle et nom, un lecteur d'écran non plus. Utilisez `findBy*`
pour les éléments qui apparaissent de façon asynchrone plutôt que des attentes manuelles. Angle React détaillé : [React Q30](react-typescript.md).

**Exemple :**

```tsx
test('shows an error when the email is invalid', async () => {
  const user = userEvent.setup();
  render(<SignupForm />);

  await user.type(screen.getByLabelText(/email/i), 'not-an-email');
  await user.click(screen.getByRole('button', { name: /sign up/i }));

  expect(await screen.findByRole('alert')).toHaveTextContent(/valid email/i);
});
```

## 🟡 Pièges seniors

### Questions

#### Q8. Pourquoi ne pas utiliser H2 pour les tests de repository ?

**Réponse :** Parce que H2 est une autre base de données. Son dialecte SQL, son système de types, son verrouillage et
le comportement de ses contraintes diffèrent de PostgreSQL, même en « mode PostgreSQL ». Les requêtes utilisant `jsonb`,
`ON CONFLICT`, les fonctions de fenêtrage, les index partiels, `citext` ou une arithmétique de dates spécifique échouent
sur H2 ou, pire, passent sur H2 et échouent en production. Les migrations Flyway écrites pour Postgres ne tournent
souvent pas du tout sur H2, et les équipes finissent par maintenir un second schéma. Utilisez **Testcontainers** pour
lancer le vrai moteur et la vraie version dans un conteneur ; avec un conteneur réutilisé et le cache de contexte de
Spring, le coût est de quelques secondes par suite.

**Exemple :**

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");
    // ...
}
```

**Pourquoi c'est un piège :** H2 rend la suite verte et rapide, ce qui ressemble à un succès. Les bugs qu'il cache sont
justement ceux spécifiques à la base, que les tests d'intégration existent pour attraper.

#### Q9. Pourquoi une suite de tests Spring est-elle lente, et comment la rendre rapide ?

**Réponse :** La cause habituelle est le **renouvellement des contextes**. Spring met en cache les contextes
d'application entre classes de test, avec leur configuration pour clé. Chaque combinaison distincte de `@MockitoBean`
(anciennement `@MockBean`), `@TestPropertySource`, profils actifs ou `@DirtiesContext` crée un nouveau contexte, et
chacun peut mettre plusieurs secondes à démarrer. Correctifs : utiliser des **slices** (`@WebMvcTest`, `@DataJpaTest`,
`@JsonTest`) au lieu de `@SpringBootTest` partout ; regrouper les beans mockés communs dans une classe de base ou une
configuration de test partagée pour que les classes partagent une même clé de cache ; supprimer `@DirtiesContext` sauf
si un test corrompt vraiment le contexte ; et exécuter les tests unitaires purs complètement hors de Spring.

**Exemple :**

```text
Log de test Spring :  "Storing ApplicationContext ... in cache"  x 37
37 contextes × ~6 s de démarrage ≈ 4 minutes passées à démarrer Spring
Après regroupement des mocks dans une classe de base : 4 contextes
```

**Pourquoi c'est un piège :** chaque `@MockitoBean` semble anodin localement. Le coût n'apparaît que lorsqu'on compte
les contextes distincts sur toute la suite.

#### Q10. Comment testez-vous un service Spring qui appelle une API HTTP externe ?

**Réponse :** Testez à trois niveaux, et n'appelez jamais le vrai tiers depuis un test automatisé. (1) **Test unitaire avec un
mock de l'interface du client** : le service dépend d'un petit port (`PatientDirectory.find(id)`), donc Mockito renvoie des
résultats et des échecs prédéfinis ; cela couvre rapidement votre logique de branchement. (2) **Test de composant de
l'adaptateur HTTP** contre un faux serveur HTTP : **WireMock** (ou MockWebServer, ou `MockRestServiceServer` pour
`RestTemplate`/`RestClient`) permet de simuler de vraies réponses et de vérifier la *requête* envoyée (chemin, en-têtes,
authentification, corps) ainsi que le comportement sur 404, 500, réponses lentes, JSON mal formé et coupures de connexion, ce
qui est exactement là où timeouts, retries et circuit breaker sont réellement vérifiés. (3) **Test de contrat** (Spring Cloud
Contract / Pact) pour que le stub ne s'écarte pas silencieusement de l'API réelle du fournisseur (voir
[Testing Q19](testing.md)) ; éventuellement quelques tests de fumée contre le bac à sable du fournisseur dans un pipeline
séparé non bloquant. Testez ce qui compte pour la résilience : le timeout se déclenche vraiment, un retry n'a lieu que pour
les appels idempotents et s'arrête après N tentatives, le fallback renvoie la réponse dégradée, et l'erreur est convertie en
votre propre exception plutôt que de laisser fuiter celle du fournisseur.

**Exemple :**

```java
@SpringBootTest
@WireMockTest(httpPort = 8089)                       // démarre WireMock pour le test
class PatientDirectoryClientTest {
    @Autowired PatientDirectoryClient client;

    @Test void returnsPatient() {
        stubFor(get("/patients/42").willReturn(okJson("{\"id\":42,\"name\":\"Ada\"}")));
        assertThat(client.find(42).name()).isEqualTo("Ada");
        verify(getRequestedFor(urlEqualTo("/patients/42")).withHeader("Authorization", matching("Bearer .+")));
    }

    @Test void timesOutInsteadOfHanging() {
        stubFor(get("/patients/42").willReturn(ok().withFixedDelay(5_000)));   // plus lent que notre timeout de 1 s
        assertThrows(DirectoryUnavailableException.class, () -> client.find(42));
    }

    @Test void retriesTwiceOn503ThenFails() {
        stubFor(get("/patients/42").willReturn(serviceUnavailable()));
        assertThrows(DirectoryUnavailableException.class, () -> client.find(42));
        verify(3, getRequestedFor(urlEqualTo("/patients/42")));               // 1 appel + 2 retries
    }
}
```

**Pourquoi c'est un piège :** un mock Mockito de `RestTemplate` ne prouve rien sur les URL, la sérialisation ou les timeouts :
il teste que vous avez appelé une méthode que vous avez vous-même configurée. Et des stubs qui ne renvoient que `200` laissent
tous les chemins d'échec non testés, alors que c'est précisément là que la dépendance externe vous fait mal (voir aussi
[Spring Q35](spring-architecture.md) sur les circuit breakers).

#### Q11. Qu'est-ce que le sur-mocking, et comment le reconnaître ?

**Réponse :** Le sur-mocking consiste à remplacer tant de collaborateurs que le test ne vérifie plus que « la méthode A
appelle la méthode B avec ces arguments », ce qui reformule l'implémentation. Symptômes : un refactoring sans changement
de comportement casse beaucoup de tests ; les tests passent alors que la fonctionnalité est cassée parce que les mocks
renvoient ce que l'auteur supposait ; la préparation est plus longue que le test. Corrigez en testant une unité un peu
plus grande (un service avec ses vrais objets du domaine, seule l'I/O étant remplacée), en utilisant des fakes pour les
repositories, et en vérifiant des résultats (valeur renvoyée, état sauvegardé, événement publié) plutôt que des
séquences d'appels.

**Pourquoi c'est un piège :** une forte couverture et beaucoup de tests verts donnent une impression de sécurité, alors
que la suite ne peut pas attraper une erreur d'intégration et résiste activement au refactoring, l'inverse de ce à quoi
servent les tests.

#### Q12. Comment tester du code qui dépend de l'heure courante ?

**Réponse :** N'appelez jamais `LocalDateTime.now()` ou `Instant.now()` directement dans le code métier. Injectez une
`java.time.Clock` (un bean Spring en production, `Clock.fixed(...)` ou une horloge de test mutable en test) et appelez
`LocalDate.now(clock)`. Il en va de même pour l'aléatoire (injecter un `Supplier<UUID>` ou un `RandomGenerator`) et
les fuseaux horaires (passer un `ZoneId` explicitement). Pour les attentes asynchrones, utilisez Awaitility avec un
timeout plutôt que `Thread.sleep`.

**Exemple :**

```java
class SubscriptionService {
    private final Clock clock;
    boolean isExpired(Subscription s) { return s.endsAt().isBefore(Instant.now(clock)); }
}

var clock = Clock.fixed(Instant.parse("2026-01-31T23:59:59Z"), ZoneOffset.UTC);
assertThat(new SubscriptionService(clock).isExpired(sub)).isFalse();
```

**Pourquoi c'est un piège :** les tests qui utilisent la vraie horloge passent pendant des mois, puis échouent un
29 février, à minuit UTC, ou sur le runner de CI situé dans un autre fuseau.

#### Q13. 80 % de couverture de code, est-ce un bon objectif ?

**Réponse :** La couverture est un bon **signal plancher** et un mauvais **objectif**. La couverture de lignes prouve
seulement que le code a été exécuté, pas que son résultat a été vérifié : un test sans assertion couvre quand même
chaque ligne. Dès que la couverture devient un but, on écrit des tests qui exécutent du code sans le vérifier (loi de
Goodhart). Utilisez-la pour trouver les zones non testées, surtout dans les modules critiques. Pour mesurer la
*qualité* des tests, utilisez le **mutation testing** (PIT pour Java, Stryker pour JS/TS) : il modifie le code
(transforme un `>` en `>=`, supprime un appel) et vérifie qu'un test échoue. Un mutant survivant est un comportement
qu'aucun test ne vérifie.

**Exemple :**

```text
Rapport PIT, PricingService :
  couverture de lignes 96 %   score de mutation 61 %
  SURVIVED: changed conditional boundary  total > 100  →  total >= 100
  => aucun test ne vérifie une commande d'exactement 100.00
```

**Pourquoi c'est un piège :** une équipe fière de ses 90 % peut quand même livrer une erreur de borne sur un seuil de
prix, parce que rien ne vérifiait la valeur limite.

#### Q14. Qu'est-ce qui rend les tests instables (flaky), et comment les gérer en équipe ?

**Réponse :** Causes courantes : **le temps** (vraie horloge, fuseaux, `Thread.sleep` pour de l'asynchrone) ; **la
dépendance à l'ordre** (état statique partagé, base non nettoyée entre les tests, test A créant des données dont
dépend le test B) ; **la concurrence** (assertion avant qu'un consommateur asynchrone ait tourné) ; **les dépendances
externes** (vrai réseau, sandbox tierces) ; et **les limites de ressources** en CI (ports, conteneurs lents, timeouts
réglés sur un portable rapide). Le processus d'équipe compte autant que les correctifs : détecter l'instabilité
(relancer les échecs et suivre les tests qui passent au retry), **mettre en quarantaine** un test instable dans un job
non bloquant avec un responsable et une échéance, corriger la cause racine, et ne jamais laisser « relance juste le
build » devenir la norme.

**Exemple :**

```java
// ⛔ attend et espère
Thread.sleep(2000);
assertThat(repo.findById(id)).isPresent();

// ✅ attend la condition, échoue avec un timeout clair
await().atMost(Duration.ofSeconds(10))
       .untilAsserted(() -> assertThat(repo.findById(id)).isPresent());
```

**Pourquoi c'est un piège :** les retries automatiques rendent le pipeline vert mais apprennent à l'équipe à ignorer le
rouge, et de vrais bugs intermittents de production (races) se cachent parmi les tests « connus pour être instables ».

#### Q15. Quel est le risque de mettre `@Transactional` sur les tests d'intégration ?

**Réponse :** Spring annule (rollback) un test `@Transactional` à la fin, ce qui est pratique pour le nettoyage mais
change le comportement. Le test, le service et le repository partagent **une seule transaction**, donc : le lazy
loading fonctionne dans le test alors qu'il lève `LazyInitializationException` en production ; les contraintes et
triggers vérifiés au commit (contraintes différées) ne se déclenchent jamais ; les handlers
`@TransactionalEventListener(AFTER_COMMIT)` ne s'exécutent jamais ; et un bug où le service a oublié `@Transactional`
est masqué parce que le test en fournissait une. Pour les tests qui exercent les frontières de transaction, n'annotez
pas le test ; nettoyez explicitement (truncate des tables, ou un schéma de conteneur neuf par classe).

**Pourquoi c'est un piège :** le test passe précisément parce qu'il enveloppe le code dans une transaction que la
production n'a pas.

#### Q16. Comment testez-vous qu'une transaction est réellement annulée ?

**Réponse :** Il faut vérifier l'état *validé* de la base après un échec ; le test ne doit donc **pas** s'exécuter dans la
transaction habituelle annulée à la fin du test (voir [Testing Q15](testing.md)) : cette enveloppe donne l'impression que tout
est annulé et masque aussi le bug où rien n'était transactionnel. Recette : (1) appelez la méthode du service avec une entrée
qui force un échec *après* une première écriture (un collaborateur simulé lève une exception, ou une contrainte est violée) ;
(2) vérifiez l'exception attendue ; (3) interrogez ensuite via une **nouvelle transaction/connexion** (appel de dépôt hors
du service, ou `JdbcTemplate`) et vérifiez que la première écriture est **absente**. Exécutez-le contre un vrai PostgreSQL via
Testcontainers, car H2 diffère sur le verrouillage et le DDL (voir [Testing Q8](testing.md)). Utilisez
`@Transactional(propagation = NOT_SUPPORTED)` ou aucun `@Transactional` sur le test, et nettoyez les données dans
`@AfterEach`. Couvrez les règles de [Spring Q16](spring-architecture.md) : une exception vérifiée n'annule pas sans
`rollbackFor`, le travail en `REQUIRES_NEW` est validé même si la transaction externe est annulée, et une exception avalée
valide. Pour les effets de bord d'un `@TransactionalEventListener(AFTER_COMMIT)`, vérifiez qu'ils ne sont *pas* déclenchés
après un rollback.

**Exemple :**

```java
@SpringBootTest
@Testcontainers
class BookingRollbackTest {
    @Autowired BookingService service;
    @Autowired AppointmentRepository appointments;
    @Autowired AuditRepository audits;
    @MockitoBean NotificationClient notifications;          // MockBean avant Spring Boot 3.4

    @Test
    void bookingIsRolledBackWhenNotificationFails() {       // pas de @Transactional sur le test
        doThrow(new IllegalStateException("smtp down")).when(notifications).confirm(any());

        assertThrows(IllegalStateException.class, () -> service.bookAndNotify(command()));

        assertThat(appointments.count()).isZero();           // la première écriture est annulée
        assertThat(audits.count()).isEqualTo(1);             // la ligne d'audit REQUIRES_NEW survit, voulu
    }
}
```

**Pourquoi c'est un piège :** avec `@Transactional` sur le test, l'assertion passe même si le service n'a aucune transaction
(la transaction du test annule tout et le contexte de persistance renvoie des entités non flushées). Un test de rollback qui
ne peut pas échouer ne vaut rien : retirez temporairement `@Transactional` du service et vérifiez que le test passe au rouge.

#### Q17. Comment mocker les appels HTTP dans les tests frontend ?

**Réponse :** Mockez à la **frontière réseau**, pas à la frontière de module. Mock Service Worker (MSW) intercepte
`fetch` et XHR et renvoie les réponses de handlers que vous définissez : votre composant, votre bibliothèque de
data-fetching (React Query, SWR) et la sérialisation tournent pour de vrai. Mocker `fetch` ou votre module d'API à la
main saute ce code et tend à dériver du vrai contrat. Définissez des handlers par scénario (succès, 500, réponse
lente, liste vide) et réutilisez-les dans Storybook et en développement local.

**Exemple :**

```ts
server.use(
  http.get('/api/orders', () => HttpResponse.json([], { status: 200 })),
);
render(<OrdersPage />);
expect(await screen.findByText(/no orders yet/i)).toBeInTheDocument();
```

**Pourquoi c'est un piège :** `jest.mock('../api')` teste que le composant appelle une fonction, pas qu'il gère la vraie
forme de réponse, l'état de chargement et les erreurs.

#### Q18. Comment faites-vous un test de charge d'une API REST avec Gatling, et comment lisez-vous les résultats ?

**Réponse :** Un test de charge répond à « comment la latence et le taux d'erreur évoluent-ils quand la charge concurrente
monte, et où cela casse-t-il ? » ; il lui faut donc un **scénario réaliste, des données réalistes et un objectif explicite**.
Gatling (outil « code d'abord » : DSL Scala/Java/Kotlin, rapports HTML) modélise un parcours utilisateur (connexion,
recherche de créneaux, réservation, annulation) avec des feeders pour les données de test (patients uniques, jetons), des
vérifications sur chaque réponse (statut, champ JSON, temps de réponse) et un **profil d'injection** qui définit la forme de
la charge. Préférez un **modèle ouvert** (`constantUsersPerSec`, `rampUsersPerSec` : de nouveaux utilisateurs arrivent à
cadence fixe quelle que soit la lenteur du système, comme dans la vraie vie) à un **modèle fermé** (`atOnceUsers`,
`constantConcurrentUsers` : un nombre fixe d'utilisateurs attend chaque réponse), car le modèle fermé ralentit ses propres
arrivées quand le serveur ralentit et masque la queue (*omission coordonnée*, voir
[Full Stack Q8](fullstack-devops-k8s.md)). Types de tests courants : **smoke** (1 utilisateur, valider le script),
**charge** (pic attendu, stable), **stress** (monter au-delà de la limite pour trouver le point de rupture et la façon
d'échouer), **endurance/soak** (des heures à charge modérée pour révéler fuites et épuisement de pools), **pic/spike**
(brusque x10). Définissez des **assertions** comme critères de réussite (`p95 < 300 ms`, `échecs < 1 %`) pour que le build
puisse échouer automatiquement. Lisez le rapport en regardant les percentiles de temps de réponse dans le temps (pas la
moyenne), les requêtes/s vs utilisateurs actifs, la répartition des erreurs, puis **corrélez avec les métriques côté serveur**
(CPU, GC, pool de connexions, BD) pour trouver la ressource saturée. Exécutez-le sur un environnement proche de la
production, jamais sur le portable qui héberge aussi l'application, et échauffez la JVM d'abord.

**Exemple :**

```java
public class BookingSimulation extends Simulation {
    HttpProtocolBuilder http = http.baseUrl("https://staging.api.example.com").acceptHeader("application/json");
    FeederBuilder<String> patients = csv("patients.csv").circular();

    ScenarioBuilder book = scenario("search and book")
        .feed(patients)
        .exec(http("search slots").get("/slots?doctor=#{doctorId}&day=2026-11-02")
            .check(status().is(200), jsonPath("$[0].id").saveAs("slotId")))
        .pause(1, 3)                                          // temps de réflexion
        .exec(http("book").post("/appointments")
            .header("Idempotency-Key", "#{randomUuid()}")
            .body(StringBody("{\"slotId\":\"#{slotId}\",\"patientId\":\"#{patientId}\"}")).asJson()
            .check(status().in(201, 409)));                   // 409 = course perdue, issue attendue

    { setUp(book.injectOpen(
            rampUsersPerSec(5).to(50).during(120),            // montée en charge
            constantUsersPerSec(50).during(600)))             // pic stable
        .protocols(http)
        .assertions(global().responseTime().percentile(95).lt(300),
                    global().failedRequests().percent().lt(1.0)); }
}
```

**Pourquoi c'est un piège :** un test vert sur une base vide, avec un seul enregistrement chaud en cache et un modèle fermé,
ne prouve rien sur la production. Le volume de données de test, l'état du cache et les temps de réflexion changent autant la
réponse que le code, et les chiffres d'un runner CI partagé ne valent que pour une comparaison *relative* entre builds. Voir
[Full Stack Q36](fullstack-devops-k8s.md) pour exploiter les résultats afin de corriger un goulot.

## 🔴 Expert / Ouvert

### Questions

#### Q19. Qu'est-ce que le contract testing piloté par le consommateur, et quand en vaut-il la peine ?

**Réponse :** Chaque **consommateur** écrit des tests qui enregistrent ce dont il a réellement besoin de l'API d'un
fournisseur (la requête, et les champs de la réponse qu'il lit). Cela produit un **contrat** (fichier Pact) publié
dans un broker. Le **fournisseur** vérifie le contrat de chaque consommateur dans son propre pipeline, contre la vraie
implémentation. Si le fournisseur supprime un champ lu par un consommateur, son build échoue avant le déploiement. Cela
remplace la plupart des tests end-to-end inter-services pour la compatibilité d'API. Rentable quand plusieurs équipes
possèdent des services qui s'appellent en HTTP ou par messages et déploient indépendamment. Pas rentable pour une seule
équipe qui déploie tout ensemble, ni pour une API publique aux consommateurs inconnus (utiliser plutôt le diff de schéma
OpenAPI et le versioning). Spring Cloud Contract est l'alternative pilotée par le fournisseur dans l'écosystème Spring.

**Exemple :**

```text
order-ui (consommateur)    -> pact : GET /orders/42 renvoie { id, status, total }
order-service (fournisseur) CI : vérifie le pact contre le vrai controller -> ✅
Un développeur retire `total` de la réponse -> la CI du fournisseur échoue : "order-ui expects total"
can-i-deploy order-service --to prod -> ❌ bloqué
```

#### Q20. Concevez la stratégie de test d'un système de dix microservices. Qu'est-ce qui tourne où ?

**Réponse :** Par service, à chaque commit : tests unitaires et tests d'intégration contre de vraies dépendances en
conteneurs (base, broker), plus des **tests de contrat** pour chaque API fournie ou consommée. Cela donne un feedback
rapide, local au propriétaire, et attrape la plupart des bugs. Au merge sur main, déployer dans un environnement partagé
et lancer une **petite suite de smoke tests** (santé, un chemin critique par service). Garder une **suite end-to-end
mince** (10–20 parcours : inscription, checkout, remboursement) sur l'environnement intégré, possédée par les équipes,
pas par un silo QA séparé. En production, utiliser du **monitoring synthétique** sur les mêmes parcours critiques, plus
des releases canary avec rollback automatique en cas de violation de SLO. À éviter : une énorme suite end-to-end
partagée qui bloque chaque déploiement, dure une heure et échoue pour des raisons que personne ne possède ; elle recrée
le couplage que les microservices devaient supprimer.

#### Q21. Quand le TDD aide-t-il, et quand ne l'utilisez-vous pas ?

**Réponse :** Le TDD (rouge → vert → refactor) aide surtout là où le comportement est bien défini et riche en logique :
prix, validation, parsing, machines à états, corrections de bugs (écrire d'abord le test qui reproduit le bug). Il
pousse vers un design testable, avec de petites unités et des dépendances explicites, et fournit gratuitement un filet
de non-régression. Il aide moins pendant les spikes exploratoires, quand on ne sait pas encore quoi construire (spike,
jeter, puis développer la vraie version en TDD), et pour le code de colle fin où un test d'intégration est la
vérification qui a du sens. Le TDD **outside-in** part d'un test d'acceptation et mocke vers le bas (école de Londres) ;
le TDD **inside-out** part du domaine et remonte (école de Chicago). Une réponse senior est pragmatique : le but est un
feedback rapide et fiable, et le TDD est un moyen parmi d'autres de l'obtenir.

#### Q22. Comment tester du messaging asynchrone (consommateurs et producteurs Kafka/RabbitMQ) ?

**Réponse :** Découpez en couches. **Testez le handler en unitaire** comme une simple méthode : pour ce message, il
produit ce changement d'état ou cet événement sortant, sans broker. **Testez le câblage en intégration** avec un vrai
broker via Testcontainers : publier un message et vérifier l'effet avec Awaitility, ce qui contrôle la sérialisation,
les noms de topics, la configuration du consumer group et la gestion d'erreurs. Testez explicitement **les chemins
d'échec** : un message empoisonné arrive dans la DLQ après les retries configurés ; une **double livraison** du même
message laisse l'état inchangé (idempotence, voir [Messaging Q13](messaging-rabbitmq-kafka.md)) ; un crash après
traitement mais avant commit rejoue le message sans dégât. Pour les schémas, ajoutez un contrôle de compatibilité
(Schema Registry) en CI.

**Exemple :**

```java
kafkaTemplate.send("orders", orderId, payload);
kafkaTemplate.send("orders", orderId, payload);           // double livraison

await().atMost(Duration.ofSeconds(10)).untilAsserted(() ->
    assertThat(paymentRepo.countByOrderId(orderId)).isEqualTo(1));
```

#### Q23. Comment garder une suite end-to-end Playwright/Cypress rapide et fiable ?

**Réponse :** Ne couvrez que les parcours utilisateur critiques ; descendez tout le reste en tests de composants et
d'API. Rendez chaque test **indépendant** : il crée ses propres données via l'API (pas via l'UI) et ne dépend pas de ce
qu'un autre test a laissé. Utilisez des **sélecteurs robustes** (rôle et nom accessible, ou `data-testid`), jamais des
chemins CSS. Appuyez-vous sur les assertions à attente automatique de l'outil plutôt que sur des timeouts fixes. Stubbez
au niveau réseau les tiers que vous ne contrôlez pas (sandbox de paiement, email). Exécutez en parallèle avec des
comptes isolés, enregistrez traces et vidéos en cas d'échec, et suivez l'instabilité par test. Limitez les retries à
un et traitez un succès au retry comme un signal d'instabilité à corriger.

**Exemple :**

```ts
test('checkout with a saved card', async ({ page, request }) => {
  const user = await createUserWithCart(request);          // préparation via l'API, pas l'UI
  await loginAs(page, user);
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
});
```

## 🎯 Scénarios réels

### S1. La suite de tests backend prend 25 minutes, et les développeurs ne la lancent plus en local

- **Symptômes :** Les tests ne tournent plus qu'en CI ; les PR attendent une demi-heure de feedback ; on enchaîne les
  commits « fix test ».

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Mesurer avant de deviner. Récupérer les durées par classe dans le rapport de build et compter les
  démarrages de contexte Spring dans les logs. Constats habituels : des dizaines de contextes distincts dus à des jeux
  de `@MockitoBean` différents et à `@DirtiesContext` ; `@SpringBootTest` utilisé pour de la logique qui n'a pas besoin
  de Spring ; un conteneur de base neuf par classe ; et des tests exécutés séquentiellement.
- **Exemple :**

  ```text
  grep -c "Started .* in" build/test-output.log   -> 41 démarrages de contexte
  10 classes les plus lentes : toutes @SpringBootTest, toutes avec des jeux de @MockitoBean différents
  ```

- **Résolution :** Convertir les tests de logique pure en JUnit simple ; utiliser des slices pour le web et la
  persistance ; regrouper les mocks dans une configuration de test partagée ; réutiliser une seule instance
  Testcontainers par JVM (conteneur statique ou `@ServiceConnection` dans une configuration partagée) ; activer
  l'exécution parallèle des tests via les forks Gradle/Maven.
- **Prévention :** Suivre la durée de la suite comme une métrique avec un budget (par exemple 5 minutes pour la porte
  de PR), et examiner en revue de code les nouveaux usages de `@SpringBootTest` et `@DirtiesContext`.

</details>

### S2. Un test passe en local et au retry, mais échoue en CI environ une fois sur dix

- **Symptômes :** L'échec porte toujours sur la même assertion, n'est jamais reproductible sur un portable, et
  « relancer » le corrige.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Chercher ce qui diffère en CI : **l'ordre des tests** (lancer la classe seule vs avec toute la
  suite ; le `MethodOrderer` aléatoire de JUnit révèle le couplage d'ordre), **le fuseau et la locale** du runner,
  **la vitesse** (un CPU plus lent fait « courir » les assertions asynchrones) et **l'état partagé** (caches statiques,
  base non nettoyée, port fixe).
- **Exemple :**

  ```text
  Runner CI TZ=UTC, portable TZ=Europe/Paris
  le test construit LocalDate.now() à 23:30 UTC -> la date diffère du « aujourd'hui » attendu à Paris
  ```

- **Résolution :** Corriger la cause racine : injecter une `Clock` et un `ZoneId` fixes, remplacer les sleeps par
  Awaitility, isoler les données par test (identifiants uniques, truncate entre les tests), utiliser des ports
  aléatoires.
- **Prévention :** Lancer volontairement la CI avec un fuseau non standard et un ordre de tests aléatoire, mettre en
  quarantaine les nouveaux tests instables avec un responsable, et publier le taux de succès au retry.

</details>

### S3. Tous les tests sont verts, mais une requête échoue en production avec une erreur de syntaxe

- **Symptômes :** Un nouvel endpoint de recherche renvoie 500 en production avec une erreur PostgreSQL ; son test de
  repository passe.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Vérifier quelle base utilisent les tests. Les tests de repository tournent sur H2 en mode de
  compatibilité, qui a accepté une fonction ou une syntaxe que PostgreSQL rejette (ou se comporte autrement sur la
  casse, `ILIKE`, les opérateurs `jsonb` ou les fonctions de date).
- **Exemple :**

  ```text
  profil de test : spring.datasource.url=jdbc:h2:mem:test;MODE=PostgreSQL
  erreur en prod : ERROR: function datediff(unknown, timestamp) does not exist
  ```

- **Résolution :** Corriger la requête, puis passer les tests de repository sur PostgreSQL via Testcontainers, avec la
  même version majeure qu'en production et les vraies migrations Flyway.
- **Prévention :** Interdire la base en mémoire pour les tests de persistance (une règle ArchUnit ou un contrôle de
  dépendances qui fait échouer le build si H2 est sur le classpath de test).

</details>

### S4. Un pur refactoring casse 200 tests alors que l'application fonctionne toujours

- **Symptômes :** Un développeur extrait une classe et renomme deux méthodes ; le comportement est inchangé (les
  vérifications manuelles et end-to-end passent), mais des centaines de tests unitaires échouent et la PR est bloquée.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les tests sont couplés à l'implémentation : ils mockent chaque collaborateur, vérifient des
  séquences d'appels internes, et testent des helpers privés rendus visibles au package « pour les tests ».
- **Exemple :**

  ```java
  verify(validator).validate(order);
  verify(mapper).toEntity(order);
  verify(repo).save(any());
  verifyNoMoreInteractions(validator, mapper, repo);
  // vérifie *comment* ça marche, pas *ce que* ça fait
  ```

- **Résolution :** Réécrire les pires cas sur une unité plus grande : vrais objets du domaine et mappers, repository
  factice, et assertions sur la valeur renvoyée et l'état sauvegardé. Supprimer les tests qui ne font que reformuler
  l'implémentation.
- **Prévention :** S'accorder sur une règle d'équipe en revue de code : ne mocker que les frontières d'I/O et les
  effets de bord sortants ; tester via les API publiques ; `verifyNoMoreInteractions` doit être justifié.

</details>

### S5. La suite end-to-end échoue 10 % du temps, et l'équipe ignore désormais ses échecs

- **Symptômes :** Les runs end-to-end nocturnes sont rouges presque tous les matins ; les relances passent en général ;
  une vraie régression a été livrée la semaine dernière parce que son échec a été écarté comme « encore instable ».

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Classer les 30 derniers échecs à partir des traces : timing (attentes fixes, animations), données
  de test partagées (deux tests utilisant le même compte), instabilité d'environnement (une dépendance en panne) et
  sélecteurs cassés par des changements d'UI. En général, deux ou trois causes expliquent la plupart des échecs.
- **Exemple :**

  ```text
  12 échecs : utilisateur partagé "e2e@test.com" modifié par un test parallèle
   8 échecs : waitForTimeout(2000) trop court en CI
   5 échecs : timeout de la sandbox de paiement
   5 échecs : vrais bugs
  ```

- **Résolution :** Donner à chaque test ses propres données créées via l'API, remplacer les attentes fixes par des
  assertions web-first, stubber la sandbox de paiement, et descendre les parcours non critiques en tests de composants.
- **Prévention :** Publier un tableau de bord d'instabilité par test, mettre en quarantaine avec responsable et
  échéance, plafonner la taille de la suite, et faire qu'un run end-to-end rouge bloque la release tant que personne
  ne l'a trié.

</details>

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q1. Qu'est-ce que la pyramide des tests, et est-ce toujours la bonne forme ?
2. Q3. Mock, stub, fake, spy — quelle différence, et quand utiliser chacun ?
3. Q8. Pourquoi ne pas utiliser H2 pour les tests de repository ?
4. Q9. Pourquoi une suite de tests Spring est-elle lente, et comment la rendre rapide ?
5. Q13. 80 % de couverture de code, est-ce un bon objectif ?
6. Q14. Qu'est-ce qui rend les tests instables (flaky), et comment les gérer en équipe ?
7. Q19. Qu'est-ce que le contract testing piloté par le consommateur, et quand en vaut-il la peine ?
8. Q20. Concevez la stratégie de test d'un système de dix microservices. Qu'est-ce qui tourne où ?
9. S1. La suite de tests backend prend 25 minutes, et les développeurs ne la lancent plus en local
10. S4. Un pur refactoring casse 200 tests alors que l'application fonctionne toujours

## 📌 Cheat-sheet

### Stratégie

> **Pour commencer :** beaucoup de tests rapides, peu de lents ; ne remplacer que l'I/O ; vérifier le comportement, pas les appels.

- **Pyramide vs trophée** — pyramide = surtout de l'unitaire ; trophée = couche d'intégration plus épaisse. *Pour des services très CRUD, les tests d'intégration sur une vraie base attrapent davantage.*
- **Frontières** — unitaire = toute l'I/O remplacée ; intégration = au moins une vraie pièce externe ; E2E = tout réel. *Se demander « où peut être le bug si ça échoue ? ».*
- **Doublures de test** — le stub fournit des données, le mock vérifie une commande sortante, le fake est une implémentation légère qui fonctionne, le spy enveloppe un vrai objet. *Préférer réel > fake > stub > mock.*
- **Bon test unitaire** — un comportement, AAA, nom descriptif, F.I.R.S.T. *Échoue pour une seule raison.*
- **TDD** — excellent pour la logique et les corrections de bugs, faible pour les spikes et le code de colle. *Outside-in (Londres) vs inside-out (Chicago).*

### Java & Spring

> **Pour commencer :** une vraie base dans un conteneur, des slices plutôt que des contextes complets, une horloge fixe.

- **Testcontainers plutôt que H2** — même moteur et même version qu'en production, vraies migrations. *`@ServiceConnection` le branche dans Spring Boot 3.1+.*
- **Cache de contexte** — chaque jeu distinct de `@MockitoBean`/propriétés/profils démarre un nouveau contexte. *Regrouper ; éviter `@DirtiesContext`.*
- **Slices** — `@WebMvcTest`, `@DataJpaTest`, `@JsonTest`. *`@SpringBootTest` seulement pour quelques tests de câblage de bout en bout.*
- **Tests `@Transactional`** — le rollback est pratique mais cache le lazy loading, les contraintes vérifiées au commit et les événements after-commit.
- **Temps** — injecter `Clock` ; Awaitility au lieu de `Thread.sleep`.
- **Mockito** — ne pas mocker les value objects, la classe testée, ni les types qui ne vous appartiennent pas.

### Signaux de qualité

> **Pour commencer :** la couverture trouve le code non testé ; le mutation testing dit si les tests vérifient vraiment quelque chose.

- **Couverture** — un plancher, pas un but. *Exécuté ≠ vérifié.*
- **Mutation testing** — PIT (Java), Stryker (JS/TS). *Mutant survivant = comportement non vérifié.*
- **Tests instables** — temps, ordre, asynchrone, données partagées, services externes. *Quarantaine avec responsable et échéance ; suivre le taux de succès au retry.*

### Frontend & inter-services

> **Pour commencer :** tester comme un utilisateur, mocker au niveau réseau, garder l'E2E pour les parcours critiques.

- **RTL** — cibler par rôle/label/texte ; `userEvent` ; `findBy*` pour l'asynchrone. *Les requêtes par rôle servent aussi de contrôle d'accessibilité.*
- **MSW** — mocker le HTTP au niveau réseau ; réutiliser les handlers dans Storybook et en dev.
- **Playwright/Cypress** — peu de parcours, données propres via l'API, sélecteurs robustes, attente automatique, un retry max.
- **Tests de contrat (Pact)** — le consommateur enregistre ses besoins, le fournisseur vérifie en CI, `can-i-deploy` bloque la release. *Remplace la plupart des E2E inter-services.*
- **Tests de messaging** — handler en unitaire ; câblage avec un broker conteneurisé ; tester doublons, DLQ et rejeu.
