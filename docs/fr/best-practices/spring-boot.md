# Bonnes pratiques Spring Boot

## 💉 Injection de dépendances & configuration

### Utilisez l'injection par constructeur

Injectez les dépendances par le constructeur, dans des champs `final`. N'utilisez pas `@Autowired` sur les champs.

**Pourquoi c'est une bonne pratique :** avec l'injection par champ, la classe ne peut pas être créée sans Spring :
un test unitaire doit passer par la réflexion ou démarrer un contexte pour remplir les champs. Les champs ne
peuvent pas être `final`, donc l'objet peut exister à moitié initialisé. Le constructeur rend les dépendances
explicites et obligatoires, et une classe qui en a trop se voit au premier coup d'œil. Depuis Spring 4.3, un
constructeur unique n'a même pas besoin de `@Autowired`.

```java
// ⛔
@Service
class OrderService {
    @Autowired private OrderRepository repository;
}

// ✅
@Service
class OrderService {
    private final OrderRepository repository;

    OrderService(OrderRepository repository) { this.repository = repository; }
}
```

### Regroupez les paramètres avec `@ConfigurationProperties`

Liez les paramètres associés à une classe typée et validée (un record convient) au lieu de disperser des
annotations `@Value`.

**Pourquoi c'est une bonne pratique :** `@Value("${payment.timeout}")` est une clé sous forme de chaîne répétée
partout où elle sert : une faute de frappe n'échoue qu'au démarrage, ou utilise silencieusement la valeur par
défaut. `@ConfigurationProperties` lie tout un préfixe dans un objet, convertit les types (`Duration`, `DataSize`,
listes), supporte `@Validated` pour qu'une valeur manquante échoue immédiatement, et fournit l'autocomplétion dans
l'IDE grâce au metadata processor.

```java
// ⛔
@Value("${payment.url}") String url;
@Value("${payment.timeout:5000}") int timeout;

// ✅
@Validated
@ConfigurationProperties("payment")
record PaymentProperties(@NotNull URI url, Duration timeout) {}
```

### Ne commitez jamais de secrets dans `application.yml`

Gardez les mots de passe, clés d'API et tokens hors du dépôt. Lisez-les depuis des variables d'environnement, un
secret monté, ou un vault.

**Pourquoi :** traité dans [Gardez les secrets hors du code et de Git](security.md#keep-secrets-out-of-code-and-git).

⛔ `spring.datasource.password: s3cr3t`
✅ `spring.datasource.password: ${DB_PASSWORD}`

## 🔁 Transactions

### Placez `@Transactional` sur les méthodes publiques des services

Déclarez les transactions dans la couche service, sur des méthodes publiques appelées depuis un autre bean.

**Pourquoi c'est une bonne pratique :** Spring applique `@Transactional` via un proxy autour du bean. Un appel
depuis une autre méthode de la *même* classe (`this.save()`) ne passe pas par le proxy, donc aucune transaction
n'est démarrée, et sur une méthode `private` l'annotation est ignorée. Rien ne vous prévient : le code s'exécute
simplement sans transaction. La couche service est aussi la bonne frontière : un cas d'usage, une transaction.
Les contrôleurs n'ont pas à connaître les transactions, et les repositories sont trop fins.

```java
// ⛔ auto-invocation : saveAll() s'exécute sans transaction
public void importAll(List<Order> orders) { saveAll(orders); }
@Transactional
public void saveAll(List<Order> orders) { ... }

// ✅ l'appelant (un autre bean) appelle la méthode transactionnelle
@Transactional
public void importAll(List<Order> orders) { ... }
```

### Gardez les transactions courtes, et marquez les lectures `readOnly`

N'appelez pas de services distants, n'envoyez pas d'emails et n'attendez rien de lent dans une transaction.
Utilisez `@Transactional(readOnly = true)` pour les requêtes de lecture.

**Pourquoi c'est une bonne pratique :** une transaction garde une connexion à la base, et souvent des verrous de
lignes, jusqu'à sa fin. Un appel HTTP de 10 secondes à l'intérieur occupe la connexion pendant 10 secondes, et
avec un pool de 10 connexions, quelques appels lents bloquent toute l'application. Si la transaction est annulée
après l'envoi de l'email, vous ne pouvez pas le « désenvoyer » : publiez un événement et agissez après le commit
(`@TransactionalEventListener`). `readOnly = true` permet à Hibernate de sauter le dirty checking et au driver
d'orienter vers un réplica.

⛔ `@Transactional void placeOrder() { repository.save(order); paymentClient.charge(order); }`
✅ enregistrer dans la transaction, débiter après le commit via `@TransactionalEventListener(phase = AFTER_COMMIT)`

### Sachez ce qui déclenche un rollback

Par défaut, seules les exceptions unchecked (`RuntimeException`, `Error`) déclenchent un rollback. Utilisez
`rollbackFor` si vous levez des exceptions checked.

**Pourquoi c'est une bonne pratique :** une exception checked levée depuis une méthode `@Transactional` *commite*
la transaction par défaut. La moitié du travail est enregistrée alors que l'appelant pense que l'opération a
échoué. Attraper une exception dans la méthode sans la relancer commite aussi. Soyez explicite quand le
comportement par défaut ne convient pas.

⛔ `@Transactional void transfer() throws TransferException` — commite sur `TransferException`
✅ `@Transactional(rollbackFor = TransferException.class)`

### Désactivez Open Session in View

Mettez `spring.jpa.open-in-view: false`.

**Pourquoi c'est une bonne pratique :** l'option est activée par défaut, et garde la session Hibernate (et une
connexion à la base) ouverte jusqu'à l'écriture de la réponse HTTP. Le lazy loading « fonctionne » alors dans les
contrôleurs et pendant la sérialisation JSON, ce qui masque les requêtes N+1 et exécute du SQL hors de toute
transaction. Sous charge, les connexions restent occupées pendant le rendu de la réponse. Une fois désactivée, une
`LazyInitializationException` vous indique de charger ce dont vous avez besoin dans le service.

⛔ `open-in-view: true` par défaut (Spring logge un warning au démarrage)
✅ `spring.jpa.open-in-view: false`

## 🌐 API REST

### Renvoyez des DTO, pas des entités

Convertissez les entités en DTO de requête / réponse (records) à la frontière du contrôleur.

**Pourquoi :** traité dans [Exposez des DTO, pas des entités](rest-api.md#expose-dtos-not-entities).

⛔ `@GetMapping("/{id}") User get(@PathVariable Long id)`
✅ `@GetMapping("/{id}") UserResponse get(@PathVariable Long id)`

### Validez les entrées avec `@Valid`

Placez des contraintes Bean Validation sur les DTO de requête et ajoutez `@Valid` sur le paramètre du contrôleur.

**Pourquoi c'est une bonne pratique :** le contrôleur est une frontière de confiance : n'importe quel client peut
envoyer n'importe quoi. Avec des contraintes sur le DTO (`@NotBlank`, `@Email`, `@Positive`), Spring rejette les
entrées invalides avec un 400 avant que votre code ne s'exécute, et toutes les règles sont déclarées au même
endroit. Sans `@Valid` sur le paramètre, les annotations sont ignorées silencieusement.

```java
// ✅
record CreateUserRequest(@NotBlank String name, @Email String email) {}

@PostMapping
UserResponse create(@Valid @RequestBody CreateUserRequest request) { ... }
```

### Gérez les erreurs à un seul endroit avec `ProblemDetail`

Convertissez les exceptions en réponses HTTP dans un `@RestControllerAdvice`, et renvoyez des corps `ProblemDetail`
(RFC 9457).

**Pourquoi c'est une bonne pratique :** des try/catch dans chaque contrôleur dupliquent la conversion et
divergent : un endpoint renvoie 404, un autre 500 pour la même erreur. Un handler global garde la cohérence, et
les services peuvent lever des exceptions métier sans rien savoir de HTTP. `ProblemDetail` (Spring 6+) est un
format standard que les clients savent lire. Ne renvoyez jamais de stack traces ni de messages d'exception de la
base au client.

```java
// ✅
@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(UserNotFoundException.class)
    ProblemDetail handle(UserNotFoundException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }
}
```

Faites de même pour les erreurs de validation, afin que les clients reçoivent les erreurs par champ et non un 400 générique :

```java
@ExceptionHandler(MethodArgumentNotValidException.class)
ProblemDetail handle(MethodArgumentNotValidException e) {
    var problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Validation failed");
    problem.setProperty("errors", e.getFieldErrors().stream()
        .collect(Collectors.toMap(FieldError::getField, FieldError::getDefaultMessage, (a, b) -> a)));
    return problem;
}
```

### Paginez les endpoints de collection

Ne renvoyez jamais une liste non bornée. Acceptez un `Pageable` (ou un curseur) et plafonnez la taille de page.

**Pourquoi :** traité dans [Paginez toujours les collections](rest-api.md#always-paginate-collections).

⛔ `List<OrderResponse> list()` → `repository.findAll()`
✅ `Page<OrderResponse> list(Pageable pageable)` → `repository.findAll(pageable)`

```yaml
spring.data.web.pageable:
  default-page-size: 20
  max-page-size: 100     # size=1000000 est plafonné silencieusement
```

## 📈 Exploitation

### Exposez health, readiness et liveness avec Actuator

Ajoutez `spring-boot-starter-actuator`, n'exposez que les endpoints nécessaires, et utilisez les groupes liveness /
readiness pour les probes Kubernetes.

**Pourquoi c'est une bonne pratique :** l'orchestrateur doit savoir s'il faut redémarrer l'application (liveness)
ou arrêter de lui envoyer du trafic (readiness). La readiness doit échouer tant que l'application démarre ou ne
peut pas joindre une dépendance indispensable ; la liveness ne doit vérifier que l'application elle-même, sinon
une panne de la base redémarre tous les pods en boucle. N'exposez pas `env`, `heapdump` ou `beans` publiquement :
ils divulguent la configuration et le contenu de la mémoire.

```yaml
# ✅
management:
  endpoints.web.exposure.include: health,info,prometheus
  endpoint.health.probes.enabled: true   # /actuator/health/liveness et /readiness
```

### Arrêtez l'application proprement

Mettez `server.shutdown: graceful` et un `spring.lifecycle.timeout-per-shutdown-phase`.

**Pourquoi c'est une bonne pratique :** lors d'un déploiement, l'ancien pod reçoit `SIGTERM`. Sans arrêt propre,
les requêtes en cours sont coupées et les clients reçoivent des erreurs à chaque mise en production. Avec, le
serveur refuse les nouvelles requêtes et attend la fin de celles en cours, jusqu'au timeout. (C'est le
comportement par défaut depuis Spring Boot 3.4.)

✅ `server.shutdown: graceful`, `spring.lifecycle.timeout-per-shutdown-phase: 20s`

## 🧪 Tests

### Utilisez des tests de slice, pas `@SpringBootTest` partout

Utilisez `@WebMvcTest` pour les contrôleurs, `@DataJpaTest` pour les repositories, et de simples tests unitaires
pour les services. Gardez `@SpringBootTest` pour quelques tests de bout en bout.

**Pourquoi :** traité dans [Utilisez des tranches de test plutôt que @SpringBootTest partout](testing.md#use-test-slices-instead-of-springboottest-everywhere).

⛔ `@SpringBootTest` pour tester un mapping JSON dans un contrôleur
✅ `@WebMvcTest(OrderController.class)` + `MockMvc`

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean OrderService service;        // seule la couche web est chargée

    @Test void returns404WhenUnknown() throws Exception {
        when(service.get(42L)).thenThrow(new OrderNotFoundException(42L));
        mvc.perform(get("/orders/42"))
           .andExpect(status().isNotFound())
           .andExpect(jsonPath("$.detail").value("Order 42 not found"));
    }
}
```

### Testez contre une vraie base avec Testcontainers

Lancez les tests de repository et d'intégration sur le même moteur de base de données qu'en production, pas H2.

**Pourquoi :** traité dans [Utilisez Testcontainers, pas H2, pour les tests de base de données](testing.md#use-testcontainers-not-h2-for-database-tests).

```java
// ✅
@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
@Testcontainers
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");
}
```
