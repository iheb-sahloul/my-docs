# Bonnes pratiques de test

## 🔺 Stratégie

### Suivez la pyramide des tests

Écrivez beaucoup de tests unitaires rapides, moins de tests d'intégration, et seulement une poignée de tests de bout en bout.

**Pourquoi c'est une bonne pratique :** un test unitaire s'exécute en millisecondes, un test d'intégration avec une
base de données en secondes, et un test de navigateur en dizaines de secondes. Une suite de 2 000 tests de bout en
bout à 20 s chacun prend 11 heures en série : les gens arrêtent de la lancer et mergent au petit bonheur. Les
tests de bout en bout échouent aussi pour des raisons sans rapport avec votre changement (réseau, timing, données
de test), ce qui habitue l'équipe à ignorer les builds rouges. Poussez chaque vérification au niveau le moins cher
capable d'attraper le bug.

```text
// ⛔ cornet de glace : tout passe par l'UI
E2E: 800   Intégration: 60   Unitaires: 40   -> build de 45 min, 1 exécution sur 10 rouge sans raison

// ✅ pyramide
Unitaires: 1500 (< 30 s)   Intégration: 200 (~ 3 min)   E2E: 15 parcours critiques
```

### Testez le comportement, pas l'implémentation

Faites des assertions sur les résultats et les effets de bord observables, pas sur les méthodes privées ou les appels internes qui ont eu lieu.

**Pourquoi c'est une bonne pratique :** un test couplé à l'implémentation casse à chaque refactoring alors que le
comportement n'a pas changé, donc les gens arrêtent de refactorer ou suppriment les tests. Vérifier que
`repository.save` a été appelé deux fois ne dit rien sur la justesse des données stockées.

```java
// ⛔ vérifie comment ça marche
verify(pricing, times(1)).applyVat(any());
verify(pricing, times(1)).applyDiscount(any());

// ✅ vérifie ce que ça produit
assertThat(service.total(cart)).isEqualByComparingTo("119.00");
```

### Écrivez un test qui échoue avant de corriger un bug

Reproduisez d'abord le bug dans un test, regardez-le échouer, puis corrigez.

**Pourquoi c'est une bonne pratique :** un correctif sans test est un bug qui attend de revenir, et vous ne pouvez
pas prouver que votre test l'aurait attrapé si vous ne l'avez pas vu échouer. Les tests de non-régression sont les
tests les plus précieux que vous possédez : chacun vient d'une vraie panne en production.

```java
// ✅ rouge d'abord : ce test échouait avec une NullPointerException avant le correctif
@Test
void total_isZero_whenCartHasNoItems() {
    assertThat(service.total(new Cart(List.of()))).isEqualByComparingTo("0");
}
```

## 🧱 Structure & nommage

### Utilisez Arrange-Act-Assert

Découpez chaque test en préparation, une seule action, et assertions, séparées par une ligne vide.

**Pourquoi c'est une bonne pratique :** quand un test mélange préparation et vérifications dans une boucle, personne
ne sait ce qui est testé ni quelle ligne a échoué. Une seule action par test signifie qu'un échec pointe vers un
seul comportement. Les tests avec plusieurs étapes « act » cachent quel appel a cassé.

```java
// ⛔
@Test
void test1() {
    var s = new CartService();
    s.add(item); assertEquals(1, s.size());
    s.add(item); assertEquals(2, s.size());
    s.clear();   assertEquals(0, s.size());
}

// ✅
@Test
void add_increasesSize() {
    // Arrange
    var cart = new Cart();
    // Act
    cart.add(item);
    // Assert
    assertThat(cart.size()).isEqualTo(1);
}
```

### Nommez les tests d'après le comportement

Nommez un test `method_expectedResult_whenCondition` ou utilisez `@DisplayName` avec une phrase complète.

**Pourquoi c'est une bonne pratique :** quand la CI signale `test1 FAILED`, il faut ouvrir le fichier pour savoir ce
qui a cassé. `withdraw_throws_whenBalanceIsInsufficient FAILED` est un rapport de bug à lui seul. Les noms servent
aussi de documentation vivante des règles du domaine.

```java
// ⛔
@Test void testWithdraw() { ... }

// ✅
@Test
@DisplayName("withdraw rejects amounts greater than the balance")
void withdraw_throws_whenBalanceIsInsufficient() { ... }
```

### Testez un comportement par test

Chaque test ne doit avoir qu'une seule raison d'échouer. Plusieurs assertions sont acceptables si elles décrivent le même résultat.

**Pourquoi c'est une bonne pratique :** avec dix assertions sans rapport dans une méthode, le premier échec cache les
neuf autres, et le nom ne peut pas toutes les décrire. De petits tests échouent indépendamment et vous disent
exactement ce qui est cassé.

```java
// ⛔ création, mise à jour et suppression dans un seul test
@Test void userLifecycle() { ... }

// ✅ un test par comportement
@Test void create_assignsId() { ... }
@Test void update_changesEmail() { ... }
@Test void delete_removesUser() { ... }
```

### Utilisez des tests paramétrés pour les tables d'entrées

Remplacez les tests copiés-collés qui ne diffèrent que par les données par `@ParameterizedTest`.

**Pourquoi c'est une bonne pratique :** cinq tests quasi identiques se désynchronisent, et les cas limites sont
sautés parce qu'en ajouter un demande plus de code répétitif. Une table rend les cas manquants visibles, et chaque
ligne est rapportée séparément.

```java
// ⛔
@Test void blank() { assertFalse(validator.isValid("")); }
@Test void spaces() { assertFalse(validator.isValid("  ")); }

// ✅
@ParameterizedTest
@ValueSource(strings = {"", "  ", "a@", "@b.com", "a b@c.com"})
void isValid_returnsFalse_forMalformedEmails(String email) {
    assertThat(validator.isValid(email)).isFalse();
}
```

## 🎭 Doublures de test

### Préférez les fakes aux mocks pour les collaborateurs avec état

Utilisez un fake en mémoire pour les repositories et les gateways. Gardez les mocks pour vérifier les interactions qui comptent.

**Pourquoi c'est une bonne pratique :** stubber `when(repo.findById(1)).thenReturn(...)` dans 40 tests, c'est 40
endroits à modifier quand la signature change, et le test prouve seulement que le stub renvoie ce que vous lui avez
dit. Un fake (basé sur une `Map`) se comporte comme le vrai : sauvegarder puis chercher fonctionne, donc les tests
se lisent comme un usage réel et survivent au refactoring.

```java
// ⛔
when(repo.findById(1L)).thenReturn(Optional.of(user));
when(repo.save(any())).thenReturn(user);

// ✅
class InMemoryUserRepository implements UserRepository {
    private final Map<Long, User> store = new HashMap<>();
    public User save(User u) { store.put(u.id(), u); return u; }
    public Optional<User> findById(long id) { return Optional.ofNullable(store.get(id)); }
}
```

### Ne mockez que ce que vous possédez ou ce qui est lent

Mockez la frontière (client HTTP, horloge, broker de messages), pas les objets valeur ni la classe testée.

**Pourquoi c'est une bonne pratique :** mocker une `List` ou un DTO donne un test de Mockito, pas de votre code.
Mocker trop en profondeur (des mocks qui renvoient des mocks) fait que le test reconstruit l'implémentation ligne
par ligne. Injectez une `Clock` pour que le code dépendant du temps soit déterministe au lieu de dormir.

```java
// ⛔ vrai temps, vrai sleep
Thread.sleep(1000);
assertTrue(token.isExpired());

// ✅ temps contrôlé
var clock = Clock.fixed(Instant.parse("2026-01-01T10:00:00Z"), ZoneOffset.UTC);
var token = new Token(Instant.parse("2026-01-01T09:00:00Z"), Duration.ofMinutes(30));
assertThat(token.isExpired(clock)).isTrue();
```

### Utilisez Mockito en mode strict et vérifiez avec intention

Utilisez `@ExtendWith(MockitoExtension.class)` (stubs stricts) et `ArgumentCaptor` quand vous devez contrôler ce qui a été envoyé.

**Pourquoi c'est une bonne pratique :** les stubs stricts font échouer le test en cas de stubbing inutilisé, donc la
préparation morte est supprimée au lieu de s'accumuler. `verify(x).send(any())` passe même si le contenu du message
est faux ; un captor vérifie la charge utile réelle.

```java
// ⛔ passe même si le corps de l'e-mail est vide
verify(mailer).send(any());

// ✅
var captor = ArgumentCaptor.forClass(Email.class);
verify(mailer).send(captor.capture());
assertThat(captor.getValue().to()).isEqualTo("ann@example.com");
```

## 🐳 Tests d'intégration

### Utilisez Testcontainers, pas H2, pour les tests de base de données {#use-testcontainers-not-h2-for-database-tests}

Exécutez les tests contre le même moteur de base de données qu'en production, dans un conteneur jetable.

**Pourquoi c'est une bonne pratique :** H2 en « mode PostgreSQL » diffère quand même : pas de `jsonb`, verrouillage
différent, comportement différent de `ON CONFLICT` et des fonctions de fenêtrage. Les tests passent, la production
échoue à la première requête native. Les conteneurs démarrent en quelques secondes, et avec `@ServiceConnection`
(Spring Boot 3.1+) il n'y a plus de câblage manuel de l'URL.

```java
// ⛔ spring.datasource.url=jdbc:h2:mem:test;MODE=PostgreSQL

// ✅
@Testcontainers
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");
}
```

### Partagez les conteneurs entre les tests

Déclarez le conteneur `static`, ou dans une classe de base ou de configuration partagée, pour qu'il démarre une fois par JVM.

**Pourquoi c'est une bonne pratique :** démarrer un conteneur par classe de test coûte 3 à 10 s chacun ; 50 classes
font des minutes. Réutiliser le conteneur et le contexte Spring garde la suite rapide. Isolez les données avec des
transactions qui font un rollback, ou nettoyez les tables entre les tests, pas avec de nouveaux conteneurs.

```java
// ⛔ un nouveau conteneur pour chaque classe
class A { @Container PostgreSQLContainer<?> pg = ...; }

// ✅ un conteneur pour toute la suite
@TestConfiguration(proxyBeanMethods = false)
class ContainersConfig {
    @Bean @ServiceConnection
    PostgreSQLContainer<?> postgres() { return new PostgreSQLContainer<>("postgres:16"); }
}
```

### Utilisez des tranches de test plutôt que `@SpringBootTest` partout {#use-test-slices-instead-of-springboottest-everywhere}

Choisissez `@WebMvcTest`, `@DataJpaTest` ou `@JsonTest` pour la couche testée. Réservez `@SpringBootTest` à quelques flux complets.

**Pourquoi c'est une bonne pratique :** `@SpringBootTest` charge toute l'application : 5 à 15 s de démarrage pour un
service typique, et chaque ensemble différent de `@MockBean` crée un nouveau contexte en cache. Une tranche ne
charge que les beans d'une couche et démarre en environ une seconde, ce qui rend réaliste l'exécution des tests à
chaque sauvegarde.

```java
// ⛔ contexte complet pour tester un contrôleur
@SpringBootTest @AutoConfigureMockMvc
class UserControllerTest { ... }

// ✅
@WebMvcTest(UserController.class)
class UserControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean UserService service;

    @Test
    void get_returns404_whenUserIsMissing() throws Exception {
        when(service.find(9L)).thenReturn(Optional.empty());
        mvc.perform(get("/users/9")).andExpect(status().isNotFound());
    }
}
```

### Testez les appels HTTP externes avec WireMock ou MockWebServer

Stubbez le service distant au niveau HTTP, y compris les échecs et les réponses lentes.

**Pourquoi c'est une bonne pratique :** appeler un vrai sandbox rend les tests lents, instables et dépendants de la
disponibilité de quelqu'un d'autre. Mocker votre propre `PaymentClient` saute la sérialisation, les en-têtes et la
conversion des erreurs, là où vivent la plupart des bugs d'intégration. Un stub HTTP permet de tester un 500, un
timeout ou un JSON malformé, ce qu'un sandbox ne peut pas produire à la demande.

```java
// ✅
wm.stubFor(get("/rates/EUR").willReturn(aResponse().withStatus(503)));
assertThatThrownBy(() -> client.rate("EUR")).isInstanceOf(RateUnavailableException.class);
```

## 🎯 Assertions & fiabilité

### Utilisez les assertions fluides d'AssertJ

Préférez `assertThat(...)` au `assertEquals` de JUnit pour les collections, les objets et les exceptions.

**Pourquoi c'est une bonne pratique :** `assertEquals(expected, actual)` voit constamment ses arguments inversés, ce
qui donne des messages d'échec déroutants. AssertJ se lit de gauche à droite, offre l'autocomplétion, et affiche un
diff utile de ce qui diffère dans une liste ou un record.

```java
// ⛔
assertTrue(names.contains("ann") && names.size() == 2);

// ✅
assertThat(names).containsExactlyInAnyOrder("ann", "bob");
assertThatThrownBy(() -> service.withdraw(acc, 500))
    .isInstanceOf(InsufficientFundsException.class)
    .hasMessageContaining("balance");
```

### N'utilisez jamais `Thread.sleep` pour attendre un traitement asynchrone

Utilisez Awaitility avec un timeout, ou rendez le code injectable et synchrone dans les tests.

**Pourquoi c'est une bonne pratique :** un sleep fixe est soit trop court (instable sur une machine de CI chargée),
soit trop long (chaque test perd des secondes). Awaitility interroge et rend la main dès que la condition est
vraie, et échoue avec un message clair en cas de timeout.

```java
// ⛔
publisher.send(event);
Thread.sleep(2000);
assertThat(repo.count()).isEqualTo(1);

// ✅
publisher.send(event);
await().atMost(Duration.ofSeconds(5)).untilAsserted(() ->
    assertThat(repo.count()).isEqualTo(1));
```

### Rendez les tests indépendants et déterministes

Pas d'état mutable partagé, pas de dépendance à l'ordre d'exécution, pas de données aléatoires sans seed, pas d'horloge réelle.

**Pourquoi c'est une bonne pratique :** un test qui ne passe qu'après un autre est un test instable en puissance :
lancez-en un seul, ou laissez JUnit les réordonner, et le build passe au rouge. Les tests instables coûtent plus
cher que l'absence de tests : une suite qui échoue 1 fois sur 20 est relancée au lieu d'être investiguée, et les
vrais échecs se perdent. Mettez en quarantaine ou corrigez un test instable le jour où il apparaît.

```java
// ⛔ l'état statique fuit entre les tests
static List<User> users = new ArrayList<>();

// ✅ état neuf pour chaque test
private List<User> users;
@BeforeEach void setUp() { users = new ArrayList<>(); }
```

### Construisez les données de test avec des builders

Utilisez de petites méthodes de fabrique ou des builders avec des valeurs par défaut raisonnables, et ne redéfinissez que ce qui intéresse le test.

**Pourquoi c'est une bonne pratique :** un constructeur à 12 arguments répété dans 80 tests casse les 80 quand un
champ est ajouté, et cache quelle valeur compte. Un builder fait ressortir le détail pertinent.

```java
// ⛔
new User(1L, "ann", "ann@x.com", "pw", true, false, null, 0, "FR", null, null, 0);

// ✅
var user = aUser().withCountry("FR").build();
```

### Utilisez la couverture comme un signal, pas comme un objectif

Suivez la couverture et échouez sur les baisses dans le code modifié, mais examinez aussi la qualité des tests (mutation testing avec PIT).

**Pourquoi c'est une bonne pratique :** un test sans assertion donne 100 % de couverture de lignes et zéro sécurité.
Viser 100 % produit des tests de getters. Le mutation testing modifie votre code (`>` en `>=`) et vérifie qu'un
test échoue ; un survivant est une vraie lacune que la couverture de lignes ne peut pas montrer. Environ 80 % sur
la logique métier avec de solides assertions vaut mieux que 95 % avec de faibles.

```java
// ⛔ exécute le code, ne prouve rien
@Test void coverage() { service.process(order); }

// ✅
@Test
void process_marksOrderPaid() {
    service.process(order);
    assertThat(order.status()).isEqualTo(Status.PAID);
}
```

### Exécutez les tests en CI sur chaque pull request

Lancez la suite complète à chaque push et bloquez le merge sur un build rouge.

**Pourquoi c'est une bonne pratique :** des tests qui ne tournent que sur le portable d'un développeur deviennent
obsolètes, et une branche principale cassée bloque toute l'équipe. Une boucle de retour de 10 minutes attrape le
bug pendant que l'auteur se souvient encore du changement ; une exécution nocturne le trouve trois commits plus
tard. Gardez la suite sous environ 10 minutes, et séparez les tests lents dans une étape distincte si nécessaire.

```yaml
# ✅ .github/workflows/ci.yml
- run: ./mvnw -B verify
```
