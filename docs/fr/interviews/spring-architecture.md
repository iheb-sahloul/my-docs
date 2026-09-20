# Spring & Architecture

## 🟢 Fondamentaux

### Core & configuration

#### Q1. Qu'est-ce que l'injection de dépendances (Dependency Injection) dans Spring, et quels sont ses avantages ?
La DI signifie qu'une classe déclare ce dont elle a besoin (via le constructeur, un setter ou un champ) et que le
conteneur Spring fournit (injecte) cette dépendance au lieu que la classe la crée elle-même.
Avantages : couplage faible entre les classes, tests unitaires bien plus simples (on peut injecter des mocks
sans toucher au câblage de production), configuration plus flexible (on change d'implémentation
sans toucher au consommateur), et cycles de vie des objets gérés par le conteneur au lieu d'appels
`new` faits à la main et éparpillés dans tout le code.

#### Q2. Quelle est la différence entre `@Component`, `@Service` et `@Repository` ?
Les trois enregistrent une classe comme bean géré par Spring via le component scanning. `@Component` est
la forme générique ; `@Service` et `@Repository` sont des spécialisations sémantiques — `@Service` marque
un bean de la couche service (surtout de la documentation/de l'intention), et `@Repository` active en plus
la traduction d'exceptions de Spring pour la couche d'accès aux données, en convertissant les exceptions propres au driver
en la hiérarchie unchecked `DataAccessException` de Spring, afin que les appelants n'aient pas à intercepter
des exceptions SQL spécifiques au fournisseur.

#### Q3. Quelle est la différence entre une classe `@Configuration` et une classe `@Component` qui déclare des méthodes `@Bean` ?
Les deux peuvent contenir des méthodes `@Bean` et les deux sont détectées par le component scanning, mais elles se comportent
différemment quand une méthode `@Bean` en appelle une autre. Une classe `@Configuration` s'exécute en **full
mode** : Spring la sous-classe avec CGLIB, et cette sous-classe intercepte chaque appel de méthode `@Bean` de sorte que
`jdbcTemplate(dataSource())` retourne le *même singleton* `DataSource` que le conteneur a déjà
créé au lieu d'exécuter à nouveau le corps de la méthode. Un simple `@Component` (ou un
`@Configuration(proxyBeanMethods = false)`) s'exécute en **lite mode** : pas de sous-classe, donc un
appel inter-`@Bean` est un appel de méthode Java ordinaire et construit silencieusement une *seconde instance non gérée* —
deux pools de connexions, deux caches, deux « singletons » — sans aucune erreur. Règle pratique :
utiliser `@Configuration` quand des méthodes `@Bean` s'appellent entre elles ; utiliser `proxyBeanMethods = false` (les
auto-configurations de Spring Boot le font) quand ce n'est pas le cas, puisque cela évite la sous-classe CGLIB et
accélère le démarrage ; ou contourner toute la question en prenant la dépendance en paramètre de méthode
(`JdbcTemplate jdbcTemplate(DataSource ds)`), ce qui fonctionne dans les deux modes.

#### Q4. Qu'est-ce que Spring Boot, et en quoi diffère-t-il de Spring « classique » ?
Spring Boot est une couche opinionated par-dessus le Spring Framework qui supprime la plupart de la configuration
manuelle. Là où Spring classique demande beaucoup de configuration XML ou Java et un serveur provisionné
séparément, Spring Boot auto-configure les beans en fonction des dépendances présentes dans le
classpath, embarque un serveur (Tomcat, Jetty ou Undertow) pour que l'application tourne comme un jar
autonome, et intègre des fonctionnalités prêtes pour la production (métriques, health checks, configuration
externalisée) d'office — ce qui explique aussi pourquoi c'est le choix par défaut pour les microservices.

#### Q5. Que fait réellement `@SpringBootApplication` ?
C'est une annotation de commodité qui regroupe trois autres annotations sur la classe principale : `@Configuration` (marque
la classe comme source de définitions de beans), `@EnableAutoConfiguration` (active l'auto-configuration
basée sur le classpath), et `@ComponentScan` (scanne le package courant et ses
sous-packages à la recherche de composants). La comprendre comme trois annotations distinctes compte dès
qu'il faut personnaliser une seule d'entre elles — par ex. exclure une classe d'auto-configuration précise
sans renoncer au component scanning.

#### Q6. `@Value` vs `@ConfigurationProperties` — quand utiliser lequel ?
`@Value("${app.timeout}")` injecte une propriété dans un champ et convient pour une valeur unique
isolée ou pour une expression SpEL. Dès qu'on a un *groupe* de paramètres liés,
`@ConfigurationProperties(prefix = "app.payment")` lié à une classe (ou, mieux, à un `record`
immuable) est le meilleur outil : tout le groupe est lié à un seul objet typé, le **relaxed binding**
fait correspondre `app.payment.max-retries`, `APP_PAYMENT_MAXRETRIES` et `maxRetries` au même champ,
les valeurs sont converties en vrais types (`Duration`, `DataSize`, enums, listes, objets imbriqués),
`@Validated` associé aux annotations Bean Validation fait **échouer l'application au démarrage** sur un
paramètre manquant ou invalide plutôt qu'à la première utilisation, et Spring Boot génère des métadonnées pour l'IDE afin de
l'autocomplétion. Les compromis de `@Value` : des chaînes éparpillées dans le code sans
endroit unique pour voir ce qu'une application accepte, pas de validation fail-fast, et une correspondance plus stricte
des noms de propriétés. Point pratique : une valeur `@ConfigurationProperties` mal orthographiée ou manquante est
détectée au boot, alors qu'une valeur par défaut `@Value` mal orthographiée peut silencieusement livrer une mauvaise valeur en production.

### Architecture

#### Q7. Qu'est-ce que l'architecture hexagonale (ports & adapters), et quel problème résout-elle ?
L'architecture hexagonale place la logique métier/domaine au centre, en exposant des **ports**
(interfaces) qui décrivent ce dont le domaine a besoin ou ce qu'il offre, avec des **adapters** qui implémentent
ces ports pour des technologies précises — un contrôleur REST et un listener de messages peuvent tous deux être
des adapters entrants appelant le même use case ; un repository JPA et un fake en mémoire peuvent tous deux
être des adapters sortants implémentant le même port de persistance. Le problème résolu : sans
cette frontière, la logique métier a tendance à accumuler des dépendances au framework et à l'infrastructure
(annotations JPA sur les entités du domaine, `HttpServletRequest` qui fuit dans les règles métier), ce
qui rend la logique centrale plus difficile à tester en isolation et l'infrastructure plus difficile à changer sans
toucher aux règles métier.

## 🟡 Pièges seniors

### Bean container & lifecycle

#### Q8. Pourquoi l'injection par constructeur est-elle généralement préférée à l'injection par champ ?
**Réponse :** L'injection par constructeur rend les dépendances explicites et immuables (champs `final`),
rend impossible la construction du bean dans un état invalide, partiellement câblé, et —
point crucial pour les tests — permet d'instancier directement la classe avec des mocks dans un simple test
unitaire, sans aucun conteneur Spring. L'injection par champ (`@Autowired` sur un champ)
nécessite de la réflexion pour positionner la valeur, ne peut pas être `final`, masque la liste des dépendances (il faut lire
toute la classe plutôt que la signature du constructeur pour savoir ce dont elle a besoin), et oblige les tests à
soit démarrer un contexte Spring, soit utiliser des frameworks de mocking basés sur la réflexion juste pour substituer une
dépendance.

**Exemple :**
```java
// Injection par champ — nécessite Spring (ou la réflexion) pour substituer un mock dans un test.
@Service
class ReportService {
    @Autowired private ReportRepository repository;
}

// Injection par constructeur — un simple test unitaire, aucun conteneur.
@Service
class ReportService {
    private final ReportRepository repository;
    ReportService(ReportRepository repository) { this.repository = repository; }
}
new ReportService(mockRepository); // ça marche tout seul, sans Spring
```

**Pourquoi c'est un piège :** l'injection par champ paraît plus simple et c'est ce que la plupart des IDE génèrent automatiquement, mais
c'est la version qui permet à un bean de se retrouver à moitié câblé et qui force chaque futur test de cette classe
à traîner le poids du conteneur Spring dont il n'avait jamais besoin.

#### Q9. Que sont les scopes de beans Spring, et quelle est l'implication en matière de thread-safety si on se trompe ?
**Réponse :** `singleton` (par défaut) crée une instance partagée pour tout l'application context ;
`prototype` crée une nouvelle instance à chaque point d'injection/requête ; `request` et `session`
sont liés à la requête web/session HTTP. Le piège : un bean de scope `singleton` est partagé entre
toutes les requêtes concurrentes traitées par l'application, donc tout champ d'instance mutable est
un état mutable partagé entre threads — un vrai bug fréquent consiste à ajouter un champ d'instance à un
`@Service` pour « juste passer une valeur entre deux méthodes » et à obtenir une corruption de données entre requêtes
sous charge, parce que ce champ est un seul champ partagé, pas un par requête.

**Exemple :**
```java
@Service
public class ReportService { // singleton par défaut — une seule instance pour toute l'app
    private String currentUser; // champ mutable partagé, PAS un par requête

    public Report generate(String user) {
        currentUser = user;              // le thread de requête A le positionne
        return buildReport(currentUser); // le thread de requête B peut déjà avoir
                                          // écrasé currentUser au moment où ceci s'exécute
    }
}
```

**Pourquoi c'est un piège :** il passe tous les tests manuels et toutes les vérifications de staging à faible trafic (une
seule requête à la fois n'entre jamais en concurrence avec elle-même) et ne casse que lorsque deux requêtes se chevauchent réellement
en production — ce qui le rend aussi exaspérant à reproduire après coup.

#### Q10. Décrivez le cycle de vie d'un bean Spring, et comment Spring résout-il les dépendances circulaires ?
**Réponse :** En gros : les définitions de beans sont lues, les instances sont créées (constructeur
appelé), les propriétés sont injectées (l'injection par setter/champ a lieu ici — *après* la construction),
les `BeanPostProcessor`s s'exécutent (avant/après l'initialisation, y compris `@PostConstruct`), puis le
bean est prêt à l'emploi ; à l'arrêt, `@PreDestroy` et `DisposableBean.destroy()` s'exécutent. Spring
résout les dépendances circulaires par *setter/champ* (A a besoin de B, B a besoin de A) grâce à un cache à trois niveaux de
références anticipées de beans, en exposant une référence à un bean pas encore totalement initialisé pour briser le cycle —
mais cette astuce ne fonctionne que pour les beans singleton créés via injection par setter/champ, pas par
injection par constructeur : deux beans dépendant l'un de l'autre uniquement via leurs constructeurs forment
une dépendance circulaire irrésoluble, et Spring échoue immédiatement au démarrage avec une erreur claire plutôt que
d'essayer de deviner.

**Exemple :**
```java
@Service class A { A(B b) {} }   // injection par constructeur
@Service class B { B(A a) {} }   // injection par constructeur
// Le démarrage échoue immédiatement : BeanCurrentlyInCreationException — réellement irrésoluble.

@Service class A2 { @Autowired B2 b; }  // injection par setter/champ
@Service class B2 { @Autowired A2 a; }  // injection par setter/champ
// Démarre normalement — Spring donne à B2 une référence anticipée, pas encore totalement initialisée, à A2
// pour briser le cycle, puis termine le câblage des deux une fois la construction achevée.
```

**Pourquoi c'est un piège :** « il suffit de passer à l'injection par champ pour corriger la dépendance circulaire » échange une
erreur de démarrage bruyante et fail-fast contre un bean utilisable avant d'être entièrement câblé — cela fait taire le
symptôme au lieu de corriger le vrai défaut de conception (deux services qui ont besoin l'un de l'autre), et
refait surface plus tard sous forme de bug plus subtil si l'un des beans fait un vrai travail pendant sa construction.

#### Q11. Quels design patterns apparaissent naturellement dans le fonctionnement de Spring lui-même ?
**Réponse :**
- **DI / IoC** : l'injection par constructeur, setter et champ implémentent directement ce pattern.
- **Singleton** : le scope de bean par défaut — `@Service` applique effectivement Singleton, une seule
  instance partagée que le conteneur injecte partout où elle est nécessaire.
- **Factory** : `ApplicationContext` et les implémentations de `FactoryBean` agissent comme des factories qui
  créent et gèrent les beans, au lieu que les appelants instancient des objets avec `new`.
- **Strategy** : injection de différentes implémentations d'une même interface selon le contexte
  (par ex. plusieurs implémentations de `PaymentProcessor` sélectionnées à l'exécution).
- **Proxy** : un objet substitut qui contrôle l'accès au vrai bean — exactement le mécanisme
  derrière `@Transactional`, la sécurité au niveau des méthodes, et l'AOP en général.
- **Template** : des abstractions comme `JdbcTemplate` prennent en charge le code répétitif d'une
  opération (ouvrir la connexion, exécuter la requête, gérer les exceptions, fermer la connexion) tout en vous laissant
  brancher uniquement la partie qui varie.

**Exemple :**
```java
// Proxy : @Transactional enveloppe le bean pour que start/commit/rollback se fassent autour de votre code.
@Transactional
public void placeOrder(Order order) { repository.save(order); }

// Template : JdbcTemplate masque le code répétitif connexion/exception/fermeture — vous fournissez
// uniquement le SQL et la fonction de mapping des lignes, les parties qui varient réellement.
List<Order> pending = jdbcTemplate.query(
    "select * from orders where status = ?",
    (rs, rowNum) -> new Order(rs.getString("id"), rs.getString("status")),
    "PENDING");
```

**Pourquoi c'est un piège :** nommer les patterns est la moitié facile ; la question de suivi qui intéresse vraiment un
recruteur est de repérer où l'abstraction fuit — par ex. supposer qu'un singleton `@Service` est
sûr pour un état d'instance mutable (Q9), ou qu'un proxy CGLIB se comporte à l'identique de l'objet réel
qu'il enveloppe (Q12). Réciter « Spring utilise Singleton, Factory, Proxy... » sans être capable de
nommer un mode de défaillance concret pour au moins l'un d'eux est une réponse superficielle.

### Proxies, AOP & transactions

#### Q12. Quelle est la différence pratique entre les proxies dynamiques JDK et les proxies CGLIB dans Spring AOP, et pourquoi est-ce important ?
**Réponse :** Spring utilise des proxies dynamiques JDK (basés sur les interfaces) quand le bean cible implémente au
moins une interface, et CGLIB (génération de bytecode par sous-classe) quand ce n'est pas le cas, ou quand
il est explicitement configuré pour toujours utiliser CGLIB. Le piège pratique : un proxy dynamique JDK ne peut
intercepter que les appels faits *via le type interface* — si vous injectez la classe concrète et appelez une
méthode qui n'est pas dans l'interface, ou faites de l'auto-invocation (Q14), il est contourné. CGLIB sous-classe la classe
cible, donc les classes `final` ou les méthodes `final` ne peuvent pas du tout être proxifiées par CGLIB — l'advice AOP
prévu (transactions, sécurité, cache) est alors silencieusement ignoré au lieu de lever une erreur, ce
qui explique pourquoi `final` sur une classe gérée par Spring ou ses méthodes est un vrai piège, pas seulement une
préférence de style.

**Exemple :**
```java
@Service
public final class PricingService { // classe final — CGLIB ne peut pas la sous-classer
    @Transactional
    public void applyDiscount(Order order) {
        order.applyDiscount();
        repository.save(order);
    }
}
// PricingService n'implémente aucune interface, donc Spring a besoin de CGLIB — mais CGLIB ne peut pas
// sous-classer une classe final, donc le proxy n'est jamais créé et @Transactional ne
// s'exécute jamais, silencieusement. Aucune erreur au démarrage ; l'annotation est simplement inerte.
```

**Pourquoi c'est un piège :** le mode de défaillance est identique à Q14/Q13 (no-op silencieux, aucune erreur nulle part),
mais la cause racine ici est un modificateur de classe qui n'a rien à voir avec le code transactionnel
lui-même — un `final` ajouté pour des raisons de « bonnes pratiques » sans rapport désactive silencieusement l'AOP.

#### Q13. Puisque `@Transactional` repose sur le pattern Proxy, que cela vous dit-il sur son utilisation sur une méthode private ?
**Réponse :** Une méthode private ne peut pas être proxifiée comme une méthode public — le proxy dynamique
surcharge/enveloppe la méthode depuis l'*extérieur* de la classe, et une méthode private n'est pas visible en dehors de
la classe pour être surchargée. Donc `@Transactional` sur une méthode private a le même mode de défaillance
pratique que l'auto-invocation (Q14) : elle est silencieusement ignorée, aucune transaction ne démarre jamais,
et rien ne vous le dit ni à la compilation ni même au démarrage.

**Exemple :**
```java
@Service
public class OrderService {
    @Transactional
    private void archive(Order order) { // un proxy ne peut jamais surcharger une méthode private
        repository.markArchived(order); // cette annotation n'a aucun effet
    }

    public void run(Order order) {
        archive(order); // même no-op silencieux que l'auto-invocation — aucune erreur nulle part
    }
}
```

**Pourquoi c'est un piège :** il est facile de supposer que « l'annotation est sur la méthode, donc elle s'applique » —
Spring ne valide jamais cela au démarrage, donc une méthode `@Transactional private` est une mine qui
paraît parfaitement correcte en code review.

#### Q14. Peut-on appeler une méthode `@Transactional` depuis une autre méthode de la même classe ?
**Réponse :** Non — ou plutôt, cela ne fonctionne silencieusement pas comme attendu. Spring implémente
`@Transactional` via un proxy enveloppant le bean ; un appel depuis l'*extérieur* de la classe passe
par ce proxy et la logique transactionnelle s'exécute, mais un appel depuis l'*intérieur* de la même classe
(auto-invocation) contourne totalement le proxy, en appelant directement la vraie méthode, donc aucune
transaction ne démarre réellement — sans aucune erreur pour vous le dire. Corrections : déplacer la méthode dans un autre
bean, injecter dans lui-même le proxy géré par l'`ApplicationContext` du même bean
(self-injection), ou se rabattre sur le weaving AspectJ à la compilation/au chargement, qui ne s'appuie pas sur le
proxying à l'exécution et n'est donc pas soumis à cette limitation.

**Exemple :**
```java
@Service
public class OrderService {
    public void placeOrder(Order order) {
        save(order); // auto-invocation — c'est un simple appel `this.save(...)`,
                      // il ne passe jamais par le proxy transactionnel
    }

    @Transactional
    public void save(Order order) {
        repository.save(order); // aucune transaction n'est réellement démarrée ici
    }
}
```

**Pourquoi c'est un piège :** le code compile, s'exécute et « a l'air » transactionnel — rien ne lève d'exception. Le
bug n'apparaît que le jour où quelque chose échoue en cours de route dans `save` et où une écriture partielle
n'est pas annulée, en production, dans des conditions qu'un test manuel du cas nominal n'a jamais exercées.

#### Q15. Comment la propagation de `@Transactional` et les règles de rollback interagissent-elles, et que fait réellement `readOnly = true` ?
**Réponse :** La propagation par défaut, `REQUIRED`, signifie « rejoindre la transaction de l'appelant s'il y en a une,
sinon en démarrer une » — donc les méthodes externe et interne partagent **une** transaction physique
et une seule décision de commit/rollback. Cela a une conséquence brutale : quand la méthode `@Transactional`
interne (appelée via un proxy, donc pas une auto-invocation, Q14) lève une exception runtime, le
proxy marque la transaction partagée **rollback-only** *avant même* que l'exception n'atteigne
l'appelant. Si la méthode externe intercepte cette exception et continue, rien n'est annulé
immédiatement — mais au moment du commit le transaction manager voit le flag rollback-only et lève
`UnexpectedRollbackException: Transaction silently rolled back because it has been marked as
rollback-only`, et *tout* le travail de la méthode externe est perdu. `REQUIRES_NEW` suspend la transaction externe
et en démarre une indépendante (une seconde connexion du pool), de sorte que le travail interne est commité ou
annulé indépendamment — le bon outil pour les enregistrements de type audit/outbox qui doivent survivre à un échec
externe, au prix de deux connexions tenues simultanément (risque d'épuisement du pool, voir S7).
`NESTED` utilise des savepoints et ne fonctionne qu'avec les transaction managers JDBC, pas avec JPA en
général. Les règles de rollback forment un axe distinct : seules les exceptions unchecked et `Error` déclenchent
un rollback par défaut (voir la cheat-sheet), donc ajoutez `rollbackFor` pour les checked. Enfin,
`readOnly = true` est un **indice**, pas un garde-fou : Spring/Hibernate l'utilisent pour sauter le dirty checking
(flush mode `MANUAL`), certains drivers passent la connexion en lecture seule, et les data sources de routage peuvent
l'envoyer vers un replica — mais savoir si un `UPDATE` égaré est réellement rejeté dépend du driver
et de la base de données, donc ne vous y fiez jamais comme frontière de sécurité.

**Exemple :**
```java
@Service
class OrderService {
    private final OrderRepository orders;
    private final AuditService audit;              // un autre bean -> passe par le proxy

    @Transactional
    public void place(Order o) {
        orders.save(o);
        try {
            audit.record(o);                        // lève une exception -> la tx est marquée rollback-only MAINTENANT
        } catch (RuntimeException e) {
            log.warn("audit failed, continuing", e); // avalée...
        }
    }                                                // ...commit -> UnexpectedRollbackException,
}                                                    // la commande est annulée aussi

@Service
class AuditService {
    @Transactional                                   // REQUIRED : rejoint la transaction de l'appelant
    public void record(Order o) { /* lève IllegalStateException */ }

    // Correction si l'audit doit être indépendant du résultat de l'appelant :
    // @Transactional(propagation = Propagation.REQUIRES_NEW)
}
```

**Pourquoi c'est un piège :** « j'ai intercepté l'exception, donc la transaction est saine » est la croyance intuitive —
et fausse. L'échec apparaît aussi *loin* de la cause (à l'accolade fermante de la méthode externe),
et `REQUIRES_NEW` ressemble à un correctif gratuit alors qu'il double discrètement l'usage des connexions.

#### Q16. Que fait réellement `flush()` sur un persistence context, et en quoi diffère-t-il de `commit()` ?
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

#### Q17. Qu'est-ce que l'Open-in-View (OSIV), pourquoi est-il activé par défaut, et pourquoi beaucoup d'équipes le désactivent-elles ?
**Réponse :** Avec `spring.jpa.open-in-view=true` (le défaut de Spring Boot — il journalise un
avertissement au démarrage à ce sujet), un `OpenEntityManagerInViewInterceptor` lie un `EntityManager` JPA au
thread de la requête pour *toute la requête HTTP*, du contrôleur jusqu'à la sérialisation JSON. Le
bénéfice est la commodité : les associations lazy peuvent encore être chargées après le retour de la méthode
de service `@Transactional`, donc un contrôleur ou un sérialiseur Jackson parcourant `order.getLines()` ne
lève pas de `LazyInitializationException`. Les coûts sont réels. Le persistence context — et,
dès que la première requête s'exécute, typiquement une **connexion de base de données du pool** — reste ouvert jusqu'à ce que la
réponse soit écrite, donc un contrôleur qui fait un appel HTTP lent, ou un client avec une connexion lente,
retient une connexion qu'il n'utilise pas et vide le pool sous charge (S7). Il masque aussi les requêtes N+1
(Q18) : les chargements lazy qui se déclenchent pendant la sérialisation ont lieu en dehors de toute méthode
de service et sont faciles à manquer en review, donc 1 + N requêtes partent sans
frontière transactionnelle autour d'elles. Le désactiver (`spring.jpa.open-in-view=false`) impose la
bonne conception : les services récupèrent exactement ce dont la réponse a besoin (`JOIN FETCH`, `@EntityGraph`, ou projections
DTO) dans la transaction, et les contrôleurs retournent des DTOs, jamais des entités. Le coût de
migration est une vague de `LazyInitializationException`s qui pointent chacune un fetch manquant — ce qui est
justement le but.

**Exemple :**
```java
// OSIV activé : compile, fonctionne, et masque un N+1 lent qui retient une connexion pendant la sérialisation.
@GetMapping("/orders/{id}")
Order get(@PathVariable long id) {
    return orders.findById(id).orElseThrow();   // retourne une entité ; les lignes se chargent en lazy pendant que
}                                               // Jackson la sérialise — hors de toute tx

// OSIV désactivé : le service charge ce dont la vue a besoin, en une requête, dans la transaction.
@Transactional(readOnly = true)
public OrderView get(long id) {
    return orders.findViewById(id);             // @Query("select new ...OrderView(...) ...")
}
// application.yml:  spring.jpa.open-in-view: false
```

**Pourquoi c'est un piège :** « OSIV est activé par défaut, donc ça doit aller » — le défaut existe par
commodité et pour les démos. Les recruteurs s'en servent pour vérifier que vous comprenez qu'une
exception de lazy-loading est un *signal de conception*, pas une nuisance à faire taire en gardant la
session ouverte plus longtemps.

### Data & caching

#### Q18. Qu'est-ce qui cause le problème des requêtes N+1 en JPA, et comment le détecter et le corriger ?
**Réponse :** Des associations JPA lazy récupérées dans une boucle déclenchent une requête par itération
au lieu d'une seule requête au total — le classique N+1 : récupérer N commandes exécute 1 requête pour les commandes,
puis N requêtes de plus, une par commande, pour charger paresseusement les lignes de chaque commande la première fois
qu'elles sont accédées. C'est invisible en code review (rien ne paraît anormal — c'est juste
`order.getLineItems()`) et invisible sur un jeu de données de dev/test de quelques lignes ; cela ne
devient visible que quand N grandit en production, où cela se manifeste par un ralentissement linéaire en N qui ressemble
à un problème de scalabilité plutôt qu'à un problème de nombre de requêtes. On le détecte en activant la journalisation SQL
(`spring.jpa.show-sql=true` plus un compteur de requêtes dans les tests, ou un outil comme les
statistics d'Hibernate/`SessionMetrics`) et en observant que le nombre de requêtes croît avec la taille du résultat au lieu de
rester constant.

**Exemple :**
```java
List<Order> orders = orderRepository.findAll();      // 1 requête
for (Order order : orders) {
    order.getLineItems().size();                      // 1 requête lazy-load supplémentaire PAR commande
}
// N commandes -> N+1 requêtes au total au lieu de 1.

// Correction : récupérer l'association dans la même requête avec un JOIN FETCH spécifique à la requête.
@Query("select distinct o from Order o join fetch o.lineItems")
List<Order> findAllWithLineItems();
```

**Pourquoi c'est un piège :** les candidats qui n'ont travaillé que sur de petits jeux de données locaux n'ont souvent
jamais vu cela échouer, donc la réponse qu'ils sortent est « il suffit de mettre `@OneToMany(fetch =
FetchType.EAGER)` » — cela corrige ce chemin de requête mais fait silencieusement en sorte que *toute* requête qui charge
un `Order` récupère aussi eagerly les lignes, y compris celles qui n'en avaient jamais besoin, échangeant un
N+1 contre un sur-chargement inconditionnel partout ; la bonne correction est un `JOIN FETCH` spécifique à la requête
ou un entity graph, pas un changement global du fetch-type sur le mapping lui-même.

#### Q19. Quel est le piège de `@Cacheable` qui retourne un objet mutable ?
**Réponse :** `@Cacheable` stocke la référence que la méthode retourne ; si c'est un objet
mutable (une `List`, une entité/DTO mutable) et qu'un appelant le modifie, chaque cache hit suivant
distribue ce même objet corrompu — le cache ne clone pas à la lecture, donc « lire depuis le
cache » et « obtenir sa propre copie privée » ne sont pas la même chose sauf si le type mis en cache est
immuable ou si le fournisseur de cache est configuré pour sérialiser/désérialiser à l'accès.

**Exemple :**
```java
@Cacheable("productLists")
public List<Product> findByCategory(String category) {
    return new ArrayList<>(repository.findByCategory(category));
}

List<Product> products = productService.findByCategory("books");
products.add(new Product("injected")); // modifie la liste en cache sur place !

// Tout appel ultérieur à findByCategory("books") retourne désormais la liste polluée —
// y compris le produit injecté — alors que rien n'a jamais été persisté.
```

**Pourquoi c'est un piège :** il n'échoue pas là où la mutation a lieu — il échoue complètement ailleurs,
sur un appel ultérieur sans rapport qui se trouve lire la même clé de cache, ce qui donne l'impression
d'un bug de corruption de données dans un chemin de code totalement différent plutôt que d'une violation du contrat de cache à la source.

### Async & threading

#### Q20. Pourquoi les méthodes `@Async` perdent-elles le contexte Spring Security ?
**Réponse :** `@Async` exécute la méthode sur un thread différent issu du pool d'un task executor, et
par défaut le contexte de Spring Security est conservé dans un `ThreadLocal` lié au thread de la requête *d'origine*
— donc le nouveau thread async ne l'a tout simplement pas, et tout contrôle de sécurité dans la
méthode async voit silencieusement un contexte non authentifié. Correction : configurer
`SecurityContextHolder.setStrategyName(MODE_INHERITABLETHREADLOCAL)`, ou, de façon plus robuste, envelopper le
task executor avec `DelegatingSecurityContextAsyncTaskExecutor`, qui propage explicitement le contexte de sécurité du
thread appelant dans le thread async.

**Exemple :**
```java
@Async
public void auditAccess(User user) {
    // S'exécute sur un thread du task-executor, pas sur le thread de requête qui s'est authentifié —
    // ceci vaut null, même si la requête appelante était entièrement authentifiée.
    Authentication auth = SecurityContextHolder.getContext().getAuthentication();
    log.info("accessed by {}", auth); // journalise "accessed by null"
}

// Correction : propager explicitement le contexte de sécurité dans l'executor async.
@Bean
public TaskExecutor taskExecutor() {
    return new DelegatingSecurityContextAsyncTaskExecutor(new ThreadPoolTaskExecutor());
}
```

**Pourquoi c'est un piège :** l'échec est silencieux, ce n'est pas une exception — un code qui lit le contexte de
sécurité pour un contrôle d'autorisation peut finir par refuser (ou, pire, autoriser par défaut)
l'accès sur la base d'un contexte vide, et le bug n'apparaît que dans le chemin async, jamais dans un
test synchrone de la même logique.

#### Q21. Quels sont les comportements par défaut des pools de threads de `@Async` et `@Scheduled`, et en quoi sont-ils inadaptés à la production ?
**Réponse :** Les deux annotations ressemblent à « exécute ça ailleurs » mais viennent avec des défauts dangereux.
Les méthodes `@Scheduled` s'exécutent sur un scheduler avec un **seul thread** par défaut
(`spring.task.scheduling.pool.size=1`) : un job lent — ou un job `fixedRate` qui prend plus de temps
que sa cadence — retarde *tous les autres* jobs planifiés de l'application, si bien que le rapport
nocturne peut démarrer avec une heure de retard parce qu'un job de cinq secondes s'enchaînait en boucle. `@Async` nécessite
`@EnableAsync` (sans lui, l'annotation est silencieusement ignorée et la méthode s'exécute simplement
de façon synchrone), et l'executor utilisé dépend de votre configuration : Spring Boot auto-configure un
`ThreadPoolTaskExecutor` (taille de base 8 et une **file effectivement non bornée**, donc un consommateur
lent construit un backlog non borné — le même échec qu'un `ExecutorService` non borné, module
1 S17), alors que Spring classique sans bean executor se rabat sur `SimpleAsyncTaskExecutor`,
qui démarre un **nouveau thread par tâche** sans aucune limite. La gestion des erreurs est la troisième lacune : une
exception levée depuis une méthode `void @Async` n'atteint jamais l'appelant (elle est seulement journalisée par
l'`AsyncUncaughtExceptionHandler` par défaut), et le `SecurityContext` et la transaction de l'appelant ne
se propagent pas (Q20). Configuration de production : déclarer un executor nommé et **borné**
(core/max/queue/`CallerRunsPolicy`) pour `@Async`, dimensionner le pool du scheduler selon le nombre de jobs
concurrents, retourner un `CompletableFuture` quand l'appelant doit observer l'échec, et
enregistrer un handler d'exceptions `AsyncConfigurer` qui déclenche une alerte.

**Exemple :**
```java
@Scheduled(fixedRate = 1_000)
void slowJob() throws InterruptedException { Thread.sleep(5_000); }   // occupe l'unique thread

@Scheduled(cron = "0 0 2 * * *")
void nightlyReport() { /* démarre en retard, ou est sauté puis regroupé, pendant que slowJob() tourne */ }

// Correction : executor borné pour @Async, pool de scheduler plus grand.
@Configuration @EnableAsync
class AsyncConfig {
    @Bean("mailExecutor")
    ThreadPoolTaskExecutor mailExecutor() {
        var ex = new ThreadPoolTaskExecutor();
        ex.setCorePoolSize(4); ex.setMaxPoolSize(8); ex.setQueueCapacity(200);
        ex.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        ex.setThreadNamePrefix("mail-");
        return ex;
    }
}

@Async("mailExecutor")
public CompletableFuture<Void> sendWelcome(User u) { /* l'échec est observable par l'appelant */ }
// application.yml:  spring.task.scheduling.pool.size: 4
```

**Pourquoi c'est un piège :** tout *fonctionne* dans une démo — les jobs se déclenchent, les mails partent. Les défauts ne
font mal qu'avec un job lent, un pic de travail ou une panne, c'est-à-dire en production, et les symptômes
(jobs en retard, mémoire qui grossit, exceptions qui disparaissent) éloignent des annotations qui
les ont causés.

### Configuration & operations

#### Q22. Quel est l'ordre de précédence entre les différentes façons de configurer une application Spring Boot ?
**Réponse :** De la priorité la plus haute à la plus basse (en gros) : arguments de ligne de commande,
propriété d'environnement `SPRING_APPLICATION_JSON`, attributs JNDI, propriétés système Java, variables
d'environnement de l'OS, `application-{profile}.properties/yml` spécifiques au profil, le
`application.properties/yml` de base, puis les annotations `@PropertySource` et les valeurs par défaut définies dans le code. L'
implication pratique : une variable d'environnement définie sur un conteneur écrasera tout ce qui est
figé dans le `application.yml` du jar, ce qui est exactement le mécanisme utilisé pour injecter des
secrets et de la config propres à un environnement sans reconstruire l'artefact pour chaque environnement.

**Exemple :**
```bash
$ SPRING_APPLICATION_JSON='{"app.timeout":"5000"}' \
  java -jar app.jar --app.timeout=9000
# --app.timeout=9000 (un argument de ligne de commande) l'emporte sur SPRING_APPLICATION_JSON,
# qui l'emporte à son tour sur ce que application.yml fige dans le jar.
```

**Pourquoi c'est un piège :** « j'ai changé la valeur dans `application.yml` et il utilise toujours l'ancienne »
est l'une des plaintes de debug de configuration les plus courantes, et la vraie cause est presque
toujours une source de priorité supérieure qui écrase silencieusement le fichier que quelqu'un a édité — la solution est
de connaître assez bien l'ordre pour vérifier d'abord la bonne couche au lieu de deviner.

#### Q23. Quels endpoints Actuator comptent en production, et lesquels faut-il faire attention à exposer ?
**Réponse :** `/actuator/health` (liveness/readiness pour les orchestrateurs), `/actuator/metrics`
(alimente Prometheus/le monitoring), `/actuator/info` (métadonnées de build/version), `/actuator/loggers`
(change les niveaux de log à chaud sans redéploiement — précieux en plein incident), `/actuator/prometheus` si
le registre de métriques est configuré pour cela. Le piège : plusieurs endpoints (`/actuator/env`,
`/actuator/beans`, `/actuator/heapdump`, `/actuator/mappings`) exposent la configuration interne,
les variables d'environnement (pouvant inclure des secrets) et la structure de l'application — ils ne devraient
jamais être exposés sans authentification sur un réseau public, et la plupart des équipes restreignent Actuator à un
port réservé à l'interne ou le placent entièrement derrière Spring Security.

**Exemple :**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, loggers
        # volontairement NON inclus : env, beans, heapdump, mappings, shutdown
  endpoint:
    health:
      show-details: when-authorized
```

**Pourquoi c'est un piège :** le starter Actuator par défaut de Spring Boot n'exposait historiquement que
`health` et `info` en HTTP, ce qui pousse les équipes à croire que « les défauts sont sûrs » — mais dès
que quelqu'un ajoute `include: "*"` par commodité pendant le debug (et oublie de le retirer),
`/actuator/env` peut divulguer des mots de passe de base de données et des clés d'API directement sur Internet.

### Web API

#### Q24. Comment gérer les exceptions globalement dans une API REST Spring Boot ?
**Réponse :** Avec `@ControllerAdvice` (ou `@RestControllerAdvice`) plus `@ExceptionHandler`,
en centralisant la gestion des erreurs au lieu de disperser des blocs try/catch dans les contrôleurs.

**Exemple :**
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(EntityNotFoundException.class)
  public ResponseEntity<ErrorBody> handleNotFound(EntityNotFoundException ex) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorBody(ex.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<ErrorBody> handleUnexpected(Exception ex) {
    log.error("unhandled exception", ex);           // détail complet côté serveur
    return ResponseEntity.internalServerError()
        .body(new ErrorBody("Something went wrong")); // message générique et sûr pour l'appelant
  }
}
```

**Pourquoi c'est un piège :** le point de niveau senior n'est pas de savoir que `@ExceptionHandler` existe, c'est de
faire correspondre chaque type d'exception au *bon* statut HTTP et à une forme de corps d'erreur cohérente, et de
ne jamais laisser une `Exception` générique non gérée divulguer une stack trace ou un détail interne (un fragment SQL,
un nom de classe interne) au client — un handler fourre-tout qui retourne
`ex.getMessage()` directement à l'appelant est un bug courant de divulgation d'information caché derrière
ce qui ressemble à une gestion d'erreurs centralisée « propre ».

#### Q25. Comment configurer CORS correctement, et quel est le piège de la combinaison d'une origine wildcard et des credentials ?
**Réponse :** Le configurer globalement via un `WebMvcConfigurer`, ou par contrôleur avec
`@CrossOrigin`. Les navigateurs rejettent (et Spring lui-même rejette à la configuration) la combinaison de
`allowedOrigins("*")` avec `allowCredentials(true)` — une origine wildcard plus cookies/credentials
permettrait à n'importe quel site d'émettre des requêtes authentifiées au nom d'un utilisateur, ce qui est exactement ce que CORS
existe pour empêcher. Si des credentials sont nécessaires, les origines doivent être une allow-list explicite, jamais un
wildcard.

**Exemple :**
```java
@Override
public void addCorsMappings(CorsRegistry registry) {
  registry.addMapping("/**")
    .allowedOrigins("https://app.example.com") // allow-list explicite, pas "*"
    .allowedMethods("GET", "POST", "PUT", "DELETE")
    .allowCredentials(true);
}
// registry.addMapping("/**").allowedOrigins("*").allowCredentials(true);
// lève IllegalArgumentException au démarrage — Spring refuse catégoriquement cette combinaison.
```

**Pourquoi c'est un piège :** un développeur sous pression de deadline qui rencontre une erreur CORS dans la console du navigateur
se rabat sur `allowedOrigins("*")` comme correction la plus rapide — ce qui est exactement la seule
combinaison qui soit échoue net (avec credentials) soit ouvre silencieusement l'API à n'importe quelle
origine (sans credentials, mais avec des données sensibles retournées quand même).

#### Q26. Pourquoi `@Valid` ne valide-t-il pas automatiquement les objets imbriqués, et quelle est la correction ?
**Réponse :** `@Valid` sur un paramètre de contrôleur valide les champs propres de cet objet, mais la
validation ne se propage **pas** automatiquement dans un champ objet imbriqué — un champ imbriqué a aussi
besoin de sa propre annotation `@Valid`, sinon Bean Validation ignore silencieusement sa validation, en
laissant passer un objet imbriqué invalide sans erreur ni avertissement.

**Exemple :**
```java
class OrderRequest {
    @NotNull String customerId;
    AddressRequest shippingAddress; // @Valid manquant — cet objet imbriqué n'est jamais validé
}
class AddressRequest {
    @NotBlank String street;
    @NotBlank String zipCode;
}

@PostMapping("/orders")
ResponseEntity<Order> create(@Valid @RequestBody OrderRequest request) {
    // request.shippingAddress.street == "" passe la validation silencieusement —
    // @NotBlank sur les champs propres de AddressRequest ne s'exécute même jamais.
}

// Correction : propager explicitement.
class OrderRequest {
    @NotNull String customerId;
    @Valid AddressRequest shippingAddress; // maintenant les contraintes imbriquées sont vérifiées aussi
}
```

**Pourquoi c'est un piège :** le DTO de premier niveau paraît entièrement annoté, compile proprement et passe tous les
tests qui n'exercent que les champs de premier niveau — la faille n'apparaît que lorsque de mauvaises données imbriquées atteignent
la base ou un système en aval, en passant une couche de validation dont tout le monde supposait qu'elle avait déjà
tout intercepté.

### Design & resilience

#### Q27. Comment structurer concrètement une application Spring Boot hexagonale en packages ?
**Réponse :** Une organisation courante : un package `domain` en Java pur (pas de Spring, pas d'annotations JPA)
contenant les entités et les règles métier ; un package `application` avec les classes de use case/service et
les interfaces de **ports** dont elles dépendent (`OrderRepository`, `PaymentGateway`) ; et un
package `infrastructure`/`adapter` avec les implémentations concrètes — un `@RestController`
adaptant HTTP vers un appel de use case, une implémentation JPA de `OrderRepository` annotée `@Repository`,
un listener de messages adaptant un message de queue vers un appel de use case. Le
mécanisme d'application qui garde réellement cela honnête dans le temps (pas seulement au premier jour) est un
test d'architecture.

**Exemple :**
```
com.example.orders
├── domain          # Java pur : Order, OrderStatus, règles métier — pas de Spring, pas de JPA
├── application     # OrderService (use case) + ports : OrderRepository, PaymentGateway
└── infrastructure
    ├── web         # OrderController — adapter entrant, traduit HTTP en appel de use case
    ├── persistence # JpaOrderRepository implements OrderRepository — adapter sortant
    └── messaging   # OrderCreatedListener — adapter entrant, traduit un message de queue
```

**Pourquoi c'est un piège :** l'organisation seule n'impose rien — rien n'empêche un développeur sous
pression de deadline d'importer `jakarta.persistence.Entity` directement dans `domain.Order`
« juste cette fois », et sans une règle ArchUnit qui l'attrape en CI, cette exception unique
devient discrètement la nouvelle norme en quelques sprints.

#### Q28. Concevez la sélection du type de paiement pour un système supportant Carte de crédit, PayPal et Bitcoin, sans que le code client sache quelle classe concrète instancier.
**Réponse :** Utiliser le pattern Factory : une `PaymentFactory` avec une méthode comme
`createPayment(String type)` qui décide en interne quelle sous-classe concrète de `Payment`
instancier et retourner. Le client demande simplement à la factory « l'implémentation de paiement dont il
a besoin » et reste découplé des implémentations concrètes — ajouter un quatrième type de paiement
plus tard revient à ajouter une nouvelle sous-classe de `Payment` et une branche dans la factory, sans toucher à chaque
site d'appel qui crée un paiement. Dans un contexte Spring, on l'implémente souvent de façon plus
idiomatique en injectant une `Map<String, Payment>` (ou une `List<Payment>` filtrée par une
méthode discriminante) et en laissant le component scanning de Spring la remplir à partir de chaque
implémentation de `Payment` annotée `@Component`, ce qui évite entièrement la chaîne `switch`/`if` de la factory.

**Exemple :**
```java
public interface Payment { void process(BigDecimal amount); }

@Component("CREDIT_CARD") class CreditCardPayment implements Payment { /* ... */ }
@Component("PAYPAL")      class PayPalPayment implements Payment { /* ... */ }
@Component("BITCOIN")     class BitcoinPayment implements Payment { /* ... */ }

@Service
class PaymentDispatcher {
    private final Map<String, Payment> payments; // Spring le câble automatiquement par nom de bean
    PaymentDispatcher(Map<String, Payment> payments) { this.payments = payments; }

    void pay(String type, BigDecimal amount) {
        payments.get(type).process(amount); // pas de classe factory, aucune chaîne switch/if
    }
}
```

**Pourquoi c'est un piège :** les candidats qui se jettent directement sur une `PaymentFactory` écrite à la main avec une
instruction `switch` n'ont pas tort, mais ils oublient que le conteneur Spring lui-même *est déjà* un
registre de beans nommés/typés — la réponse idiomatique Spring remplace une classe qu'il faudrait
maintenir par une `Map` que le conteneur remplit gratuitement, et un recruteur qui demande « comment feriez-vous
cela spécifiquement dans Spring » vérifie cette reconnaissance.

#### Q29. Quand recourir au pattern Strategy avec des beans Spring plutôt qu'à un simple `if`/`switch` ?
**Réponse :** Strategy mérite sa complexité quand l'ensemble des comportements est appelé à grandir (nouveaux
fournisseurs de paiement, nouvelles règles de tarification, nouveaux canaux de notification) et que chaque comportement est
assez substantiel pour mériter sa propre classe et ses propres tests — injecter `List<PricingStrategy>` et
en sélectionner une via une méthode prédicat garde chaque stratégie testable indépendamment et permet d'en ajouter une
nouvelle sans toucher au code existant (principe ouvert/fermé). Un simple `if`/`switch` est
le bon choix quand les branches sont réellement fixes, peu nombreuses et peu susceptibles de croître — introduire une
hiérarchie Strategy complète pour deux branches permanentes est de la sur-ingénierie qui rend le code
plus difficile à lire, pas plus facile.

**Exemple :**
```java
interface PricingStrategy { boolean supports(CustomerTier tier); BigDecimal price(Order o); }

@Service
class PricingService {
    private final List<PricingStrategy> strategies;
    PricingService(List<PricingStrategy> strategies) { this.strategies = strategies; }

    BigDecimal price(Order order, CustomerTier tier) {
        return strategies.stream()
            .filter(s -> s.supports(tier))
            .findFirst()
            .orElseThrow()
            .price(order);
    }
}
// Ajouter un nouveau tier = un nouveau @Component implémentant PricingStrategy — PricingService
// lui-même ne change jamais.
```

**Pourquoi c'est un piège :** « toujours utiliser Strategy plutôt que `if`/`switch`, c'est plus SOLID » est une
surcorrection — une réponse senior nomme le vrai critère (cet ensemble de branches grandit-il
avec le temps, et chacune est-elle substantielle) au lieu de traiter un pattern comme universellement supérieur
à une simple condition.

#### Q30. Qu'est-ce que le pattern circuit breaker, et quand un service en a-t-il réellement besoin ?
**Réponse :** Un circuit breaker enveloppe les appels vers une dépendance susceptible d'échouer et suit leur
taux d'échec ; dès que les échecs dépassent un seuil, il « s'ouvre » et échoue rapidement (sans même
tenter l'appel) pendant une période de refroidissement, puis autorise un nombre limité d'appels d'essai
(« half-open ») pour tester la récupération avant de se refermer complètement. Il compte spécifiquement quand une dépendance aval lente
ou défaillante ferait sinon s'empiler les appelants en attente sur elle
(épuisant leurs propres pools de threads, cf. S7/S8) et propager la panne en amont — un service
appelant un aval instable parmi plusieurs doit échouer rapidement sur celui-là et continuer à servir
tout le reste, plutôt que de laisser des threads faire la queue en attendant une dépendance qui ne reviendra pas
de sitôt. Resilience4j est l'intégration courante avec Spring Boot (remplaçant Netflix
Hystrix, désormais EOL).

**Exemple :**
```java
@CircuitBreaker(name = "inventoryService", fallbackMethod = "fallback")
public Stock checkStock(String sku) {
    return inventoryClient.getStock(sku); // échoue rapidement dès que le breaker est ouvert,
                                           // au lieu de bloquer sur un aval en panne
}

private Stock fallback(String sku, Throwable t) {
    return Stock.unknown(sku); // dégrader proprement plutôt que propager l'échec
}
```

**Pourquoi c'est un piège :** les candidats décrivent souvent le pattern correctement mais ne savent pas dire *quand* il est
justifié — ajouter un circuit breaker autour de chaque appel aval sans considération du rayon
d'impact relève du cargo-culting de la résilience, tandis que l'omettre sur l'unique appel qui peut réellement se propager
en cascade (un pool de threads partagé, cf. S8) laisse le vrai risque sans réponse.

## 🔴 Expert / Ouvert

### Architecture & extensibility

#### Q31. Comment migreriez-vous un monolithe existant vers une architecture hexagonale de façon incrémentale, sans réécriture big-bang ?
Commencer par les coutures qui existent déjà naturellement — choisir un module borné et bien compris
(souvent celui qui change le plus souvent, puisque c'est là que le bénéfice se cumule le plus vite) et définir
ses ports en premier : de quoi ce module a-t-il besoin du monde extérieur, et qu'offre-t-il ? Déplacer
sa logique métier derrière ces interfaces sans changer le comportement, compléter les implémentations
d'adapters pour ce qui existe déjà (le repository JPA existant devient la première
implémentation d'une nouvelle interface de port), et ajouter d'abord une suite de tests de caractérisation si elle
n'existe pas, afin que le refactoring ait un filet de sécurité. Répéter module par module ; l'erreur à éviter est de
tenter de définir le modèle de domaine « final » de tout le système dès le départ — c'est exactement le
genre d'effort de design up-front massif qui cale en plein milieu d'une migration et ne livre jamais. Utiliser
une règle ArchUnit dès le premier jour sur les modules *convertis* pour empêcher la régression, même si des
modules non convertis la violent encore.

#### Q32. Concevez un système d'extension de type plugin dans Spring afin qu'un nouveau comportement puisse être ajouté sans modifier le code existant.
Définir une interface (un port) représentant le point d'extension — par ex. `NotificationChannel` avec
`send(Notification)` et `supports(ChannelType)`. Laisser le component scanning de Spring collecter chaque
implémentation automatiquement via `List<NotificationChannel>` injectée dans un bean dispatcher,
et faire en sorte que le dispatcher sélectionne la ou les bonnes en appelant `supports()` plutôt que de coder en dur une
vérification de type. Ajouter le support de l'email, du SMS et des notifications push revient alors à ajouter trois
nouvelles classes annotées `@Component` — le code du dispatcher ne change pas, ce qui satisfait le
principe ouvert/fermé. Si les plugins doivent être réellement externes (chargés depuis des jars séparés à
l'exécution, non compilés dans l'artefact principal), le class scanning de Spring ne traversera pas proprement les
frontières de classloader — c'est le point où `ServiceLoader` ou un framework de plugins explicite
(avec sa propre stratégie de classloader par plugin) devient nécessaire à la place.

#### Q33. Comment décidez-vous entre une préoccupation transverse basée sur l'AOP (comme `@Transactional`, `@Cacheable` ou une annotation personnalisée) et son écriture explicite dans le corps de la méthode ?
L'AOP mérite son coût quand la préoccupation est réellement orthogonale à la logique métier et s'applique
uniformément à de nombreuses méthodes avec la même règle — transactions, cache et journalisation d'audit sont
les cas d'école car le « comment » est identique partout où ils sont utilisés et l'annotation rend
l'intention visible au site d'appel. Le coût est pourtant réel : l'AOP introduit les limitations de proxy
de Q14/Q13/Q12 (auto-invocation, méthodes private, classes `final`), rend le flux d'exécution réel
moins évident à la seule lecture du corps de la méthode, et peut surprendre un mainteneur
qui ne sait pas que l'annotation déclenche tout un aspect. Préférer le code explicite quand la préoccupation
varie sensiblement d'un cas à l'autre, quand la debuggabilité pendant un incident compte plus que
le DRY, ou quand l'équipe s'est déjà brûlée sur un piège de proxy AOP dans ce code même
— un code explicite qui dit exactement ce qu'il fait est parfois le choix le plus senior, pas le
moins sophistiqué.

#### Q34. Comment utiliser les événements applicatifs dans un monolithe Spring, et quel est le piège de `@TransactionalEventListener` ?
`ApplicationEventPublisher` permet à un service d'annoncer « OrderPlaced » sans savoir qui s'y intéresse
(email, inventaire, analytics), ce qui découple les modules dans un monolithe et constitue le
tremplin naturel vers les ports hexagonaux (Q27, Q31) et, plus tard, le messaging. Un simple `@EventListener`
s'exécute *de façon synchrone, sur le thread de l'émetteur, dans sa transaction* — donc l'échec d'un
listener annule la commande, et un listener lent ralentit la requête. C'est rarement ce que l'on
veut pour des effets de bord. `@TransactionalEventListener` (phase par défaut `AFTER_COMMIT`) corrige la
première moitié : le listener ne s'exécute que si la transaction a réellement été commitée, donc aucun email de
confirmation ne part pour une commande annulée. Son piège est l'image miroir : à
`AFTER_COMMIT` la transaction d'origine est terminée, donc un listener qui écrit en base de données n'est
**pas** couvert par une transaction — `@Transactional` dessus est ignoré sauf s'il est
`REQUIRES_NEW` — et si le listener échoue, ou si la JVM meurt entre le commit et la distribution,
l'événement est **perdu**, car il ne vivait qu'en mémoire. Si l'effet de bord ne doit pas être perdu (facturation,
événement d'intégration vers un autre service), persister l'intention dans la même transaction et la livrer
séparément : le **pattern outbox** (module 4 Q26) — ou, dans un monolithe modulaire, le registre de
publication d'événements de Spring Modulith, qui stocke les événements jusqu'à ce que leurs listeners aient terminé. Ma
règle : `@EventListener` pour les réactions dans la transaction qui doivent réussir ensemble ; 
`@TransactionalEventListener(AFTER_COMMIT)` pour les effets de bord best-effort (éviction de cache,
notifications) ; un outbox pour tout ce qui a une exigence de durabilité. Ajouter `@Async` (avec un
executor borné, Q21) si le listener est lent, en acceptant que l'ordre et le contexte de sécurité
ne soient plus garantis.

### Multi-tenancy & security

#### Q35. Comment concevriez-vous la multi-tenancy dans une application Spring Boot / JPA, et quels sont les pièges ?
Il existe trois modèles d'isolation, et le choix est une décision métier avant d'être technique.
**Database-per-tenant** offre l'isolation la plus forte, la sauvegarde/restauration par tenant et le
contrôle des voisins bruyants, mais coûte un pool de connexions par tenant et une charge opérationnelle qui
croît linéairement (des centaines de tenants = des centaines de pools et de migrations à exécuter). **Schema-per-tenant**
(schémas PostgreSQL) partage le serveur mais isole quand même les données et permet un `SET search_path`
par connexion ; c'est un bon compromis jusqu'à ce que le nombre de tenants atteigne les milliers
et que les migrations de schémas deviennent le goulot d'étranglement. **Schéma partagé avec un discriminant `tenant_id`**
est le moins cher et passe à l'échelle pour de nombreux petits tenants, mais l'isolation n'est aussi forte que le
`WHERE tenant_id = ?` de chaque requête — un filtre oublié est une fuite de données inter-tenants — donc l'appuyer
sur une protection au niveau de la base : la **row-level security** de PostgreSQL avec le tenant positionné par
transaction, et le `@TenantId` d'Hibernate (6.x) ou un filtre pour que le code applicatif ne puisse pas l'oublier.
Dans Spring la plomberie est la même pour les deux premiers : résoudre le tenant tôt (un filtre servlet
lisant un claim JWT ou un sous-domaine), le stocker dans un holder à portée requête, et utiliser un
`AbstractRoutingDataSource` ou le `CurrentTenantIdentifierResolver` + le
`MultiTenantConnectionProvider` d'Hibernate pour choisir la connexion. Les pièges : (1) **la propagation du contexte** —
le tenant vit dans un `ThreadLocal`, donc `@Async`, les jobs planifiés et les consommateurs de messages le perdent
exactement comme le `SecurityContext` (Q20) ; un job en arrière-plan doit positionner le tenant explicitement et le nettoyer
dans un `finally`. (2) **Les caches** — les clés `@Cacheable` doivent inclure l'id du tenant sinon le tenant A lit
la valeur en cache du tenant B (voir Q19 pour le piège apparenté de l'objet en cache). (3) **Le dimensionnement des pools** avec
des pools par tenant. (4) **Les migrations** doivent être exécutées sur tous les schémas/bases et être rejouables
(Flyway par tenant, module 3 Q25). (5) **Les tests** : un test automatisé qui demande la même
ressource en tant que deux tenants et vérifie l'isolation est le seul filet de régression fiable. Je commencerais
par le design schéma partagé + RLS sauf si un contrat client exige une isolation physique, et
je garderais le résolveur de tenant derrière une seule interface afin qu'un gros client puisse plus tard être déplacé vers sa propre
base sans toucher au code métier.

#### Q36. L'autorisation doit-elle vivre dans des règles d'URL, dans la method security, ou les deux ?
Les deux, car elles protègent contre des erreurs différentes. Les règles d'URL dans la
`SecurityFilterChain` (`authorizeHttpRequests`) sont grossières, centralisées et évaluées *avant*
l'exécution de tout contrôleur : « tout ce qui est sous `/admin/**` requiert `ROLE_ADMIN` », « `/actuator/**` est
interne uniquement ». Leur faiblesse est qu'elles sont indexées sur des chemins, donc un nouvel endpoint sous un chemin
inattendu, une particularité de normalisation de chemin (slash final, caractères encodés), ou le même
service atteint par un autre point d'entrée (un listener de messages, un job planifié, un autre
contrôleur) n'est pas protégé. Les règles sont évaluées **dans l'ordre, la première qui correspond gagne**, donc un
`permitAll()` large placé au-dessus d'une règle spécifique l'emporte silencieusement — et `anyRequest().authenticated()` (ou
`denyAll()`) doit venir en dernier, faisant du « deny by default » la base. La method security
(`@EnableMethodSecurity`, `@PreAuthorize`) place la règle à côté du code qu'elle protège et peut
exprimer des décisions **de niveau métier** que les URL ne peuvent pas : « seul le propriétaire de la commande, ou un
agent du support, peut la lire » (`@PreAuthorize("@orderAccess.canRead(#id, authentication)")`,
`@PostAuthorize` sur l'objet retourné). Cette dernière catégorie — **l'autorisation au niveau objet** —
est le problème n°1 de l'OWASP (broken access control / IDOR), et elle *ne peut pas* se faire avec des règles d'URL :
`GET /orders/123` et `GET /orders/124` ont le même chemin. La method security est implémentée avec
des proxies AOP, donc les limitations de Q14/Q13/Q12 s'appliquent : un `@PreAuthorize` sur une méthode appelée depuis
la même classe, ou sur une méthode `private`, n'est silencieusement pas appliqué — la raison classique pour laquelle un
test de sécurité passe en isolation alors que la faille existe en production. Mon défaut : des règles d'URL pour
les règles de périmètre grossières en deny-by-default ; `@PreAuthorize` sur la couche *service* (là où tous les
points d'entrée convergent) pour les contrôles de rôle et de propriété ; et un test par use case protégé qui
prouve le cas négatif (un mauvais utilisateur reçoit un 403/404).

## 🎯 Scénarios réels

### S1. Un service fonctionne parfaitement en développement local mais échoue immédiatement après le déploiement
- **Symptômes :** Tous les tests locaux et de CI passent ; le même jar échoue au démarrage, ou démarre mais plante à la
  première requête, une fois déployé dans un vrai environnement.
- **Diagnostic :** Comparer d'abord la configuration, pas le code — vérifier le profil actif
  (`spring.profiles.active`), les variables d'environnement, et quel `application-{profile}.yml`
  est réellement chargé dans cet environnement (l'ordre de précédence de Q22). Vérifier les
  ressources spécifiques à l'environnement supposées exister (une base de données, un fichier de secrets, un chemin réseau)
  et qui ne sont tout simplement pas accessibles depuis l'environnement déployé comme elles le sont depuis la machine
  d'un développeur.
- **Exemple :**
  ```yaml
  # application.yml, versionné dans le repo — un profil "dev" pointant vers une BD en mémoire.
  spring:
    profiles:
      active: dev
  ---
  spring:
    config:
      activate:
        on-profile: dev
    datasource:
      url: jdbc:h2:mem:testdb   # correct pour le dev local, et silencieusement toujours actif si
                                 # SPRING_PROFILES_ACTIVE=prod n'est jamais positionné au déploiement
  ```
- **Résolution :** Une fois la config réellement manquante/différente ou la dépendance inaccessible
  identifiée, corriger le manque précis — généralement une variable d'environnement manquante, une
  chaîne de connexion non résolue, ou une politique de firewall/réseau bloquant un appel qui fonctionnait en local.
- **Prévention :** Garder les environnements aussi proches de l'identique que possible (même runtime
  conteneurisé en local et en production via Docker, cf. module 6), et échouer vite et bruyamment au
  démarrage (un health check ou un contrôle de cohérence `@PostConstruct`) plutôt qu'à la première requête
  côté utilisateur.

### S2. Une API REST est lente, mais seulement en production — le même endpoint est rapide en local et en staging
- **Symptômes :** La latence p99 en production est bien pire qu'en staging pour un endpoint dont la logique
  n'a pas changé, et elle n'est pas constamment lente — elle varie.
- **Diagnostic :** La production a un volume de données et une concurrence que le staging n'a pas — vérifier si le
  chemin lent implique une requête de base de données dont le plan d'exécution se dégrade avec la taille réelle des données (index
  manquant qui n'importait pas sur un petit jeu de données de staging), ou s'il s'agit de contention (Q9, le
  scénario S16 du module 1 de Q22) reproductible uniquement sous la charge concurrente réelle de la production.
  Le tracing distribué (S15) ou le flame graph d'un outil APM localisera généralement directement
  le span lent.
- **Exemple :**
  ```sql
  -- Rapide en staging (10k lignes) — un full scan y est invisible à cette taille.
  select * from orders where customer_id = ?;

  -- Même requête en production (50M lignes) : explain confirme un sequential scan,
  -- car customer_id n'a jamais été indexé.
  -- Seq Scan on orders (cost=0.00..812345.00 rows=1 width=128)

  create index idx_orders_customer_id on orders(customer_id); -- la vraie correction
  ```
- **Résolution :** Ajouter l'index manquant, corriger la requête N+1 (Q18), ou traiter le point de
  contention précis une fois identifié depuis la trace — résister à l'envie de deviner et d'optimiser
  quelque chose que la trace n'a pas réellement incriminé.
- **Prévention :** Faire des tests de charge avec un volume de données à l'échelle de la production avant de livrer un nouveau chemin de requête,
  et garder le tracing distribué activé par défaut en production pour que ce diagnostic prenne des minutes,
  pas une enquête de plusieurs jours.

### S3. Les changements dans `application.properties` ne semblent pas pris en compte après une mise à jour de config
- **Symptômes :** Une valeur de configuration a été changée et redéployée, mais l'application en cours d'exécution
  se comporte toujours selon l'ancienne valeur.
- **Diagnostic :** Vérifier l'ordre de précédence (Q22) — une source de priorité supérieure (une variable d'environnement
  définie sur le conteneur, un argument de ligne de commande figé dans le script de démarrage) peut
  écraser le fichier qui a été édité. Vérifier aussi si le *mauvais profil* est actif, de sorte que le
  fichier édité n'est même pas celui qui est chargé, ou si le déploiement a réellement livré la nouvelle
  config (une image de conteneur périmée, une config figée au build plutôt que montée à
  l'exécution).
- **Exemple :**
  ```bash
  # application.properties a été édité et redéployé :
  # app.timeout=9000

  # ...mais l'environnement propre du conteneur définit toujours l'ancienne valeur, qui l'emporte :
  $ env | grep APP_TIMEOUT
  APP_TIMEOUT=3000   # une variable d'env de l'OS bat toujours le fichier properties (Q22)
  ```
- **Résolution :** Une fois la source réellement active identifiée, éditer celle-là — ou, si l'objectif
  de conception est « la config doit toujours venir de ce seul fichier », supprimer la surcharge de priorité supérieure
  à l'origine du conflit.
- **Prévention :** Journaliser le profil actif et un résumé des valeurs de config clés au démarrage, et
  standardiser sur une seule source de vérité claire par environnement (par ex. « les variables d'env du conteneur gagnent toujours,
  et c'est le seul endroit où les secrets/valeurs propres à l'environnement sont définis ») pour que cette ambiguïté ne
  se reproduise pas.

### S4. Un service Spring Boot plante ou ne répond plus sous forte charge
- **Symptômes :** Le service gère bien la charge normale mais plante, redémarre ou cesse totalement de répondre
  dès que le trafic franchit un certain seuil.
- **Diagnostic :** Distinguer l'épuisement de ressources (heap — le scénario OOM du module 1 ; pool de threads —
  Q21 du module 1, S7 ci-dessous ; pool de connexions — S7 ci-dessous) d'un vrai bug qui ne se déclenche
  que sous concurrence (une race condition, le piège de l'état mutable du singleton de Q9). Les métriques et un
  thread dump pris *pendant* l'incident (pas après le redémarrage, qui fait perdre les preuves) permettent de distinguer
  cela rapidement.
- **Exemple :**
  ```
  "http-nio-8080-exec-142" #142 waiting for monitor entry
     java.lang.Thread.State: BLOCKED (on object monitor)
     at com.example.ReportService.generate(ReportService.java:22)
     - waiting to lock <0x000000076ab62208> (a com.example.ReportService)
  # 140+ threads de requête BLOCKED sur le monitor du même singleton — le piège du champ mutable de Q9
  # qui se transforme en blocage complet du traitement des requêtes sous une vraie concurrence.
  ```
- **Résolution :** Dépend entièrement de la ressource épuisée — augmenter le pool/
  heap/nombre d'instances concerné, ou corriger le bug de concurrence si c'est ce que montre réellement un thread dump.
- **Prévention :** Faire des tests de charge pour trouver le vrai point de rupture avant que le trafic de production ne le trouve,
  et placer des circuit breakers (Q30) et du rate limiting devant le service pour qu'un pic de trafic
  se dégrade proprement au lieu de planter net.

### S5. L'application context échoue au démarrage avec une erreur « no unique bean » ou de conflit de beans
- **Symptômes :** Le démarrage échoue avec `NoUniqueBeanDefinitionException` ou similaire, généralement juste
  après l'ajout d'une seconde implémentation d'une interface qui n'en avait qu'une seule auparavant.
- **Diagnostic :** Spring ne peut pas décider quel bean injecter quand plus d'un candidat correspond
  au type d'un point d'injection sans qualification supplémentaire — c'est un signal de conception, pas seulement un
  bug de câblage, puisque cela signifie que le code a été écrit en supposant qu'il n'y aurait jamais qu'une
  seule implémentation.
- **Exemple :**
  ```
  Parameter 0 of constructor in com.example.OrderController required a single bean,
  but 2 were found:
      - creditCardPayment
      - payPalPayment
  ```
  ```java
  // Correction : être explicite sur l'intention plutôt que de laisser l'ambiguïté.
  @Primary
  @Component class CreditCardPayment implements Payment { }

  // ou, si le consommateur veut réellement toutes les implémentations (le pattern Strategy de Q29) :
  OrderController(List<Payment> payments) { ... }
  ```
- **Résolution :** Si l'une doit réellement être la valeur par défaut, la marquer `@Primary`. Si le consommateur
  a besoin d'une *précise*, utiliser `@Qualifier("beanName")`. Si le consommateur veut en fait *toutes*
  les implémentations, changer le point d'injection du type interface vers `List<Interface>` au lieu de
  lutter contre l'ambiguïté.
- **Prévention :** Quand on ajoute une seconde implémentation d'une interface existante, vérifier immédiatement
  chaque point d'injection de cette interface et décider délibérément (primary, qualifié, ou
  collecté en liste) plutôt que de laisser l'erreur du compilateur/conteneur imposer une correction précipitée.

### S6. Un endpoint d'API renvoie par intermittence `401 Unauthorized` pour des requêtes qui devraient être authentifiées
- **Symptômes :** Le même client, avec les mêmes credentials, obtient parfois une réponse réussie et
  parfois un `401`, sans schéma évident du côté client.
- **Diagnostic :** Causes courantes dans un contexte Spring Security : l'expiration du token en course avec le
  timing de la requête (un token qui expire en cours de session, surtout des JWT à courte durée de vie sans gestion correcte du
  refresh) ; le contexte de sécurité qui ne se propage pas à travers une frontière async (le scénario `@Async`
  de Q20, si l'endpoint fait du travail async avant le contrôle de sécurité) ; ou un
  déploiement avec load balancer où l'authentification par session n'est en fait pas partagée/sticky entre les instances, si bien qu'une requête
  atterrissant sur une autre instance que celle qui l'a authentifiée apparaît comme non authentifiée.
- **Exemple :**
  ```java
  @Async
  public void enforceAndAudit(String userId) {
      // SecurityContextHolder est vide sur ce thread (Q20) — un contrôle d'autorisation
      // placé ici échoue de façon imprévisible, uniquement sur les requêtes qui passent par ce chemin.
      if (SecurityContextHolder.getContext().getAuthentication() == null) {
          throw new AccessDeniedException("no security context on async thread");
      }
  }
  ```
- **Résolution :** Corriger la logique de refresh du token et les marges d'expiration pour la première cause ; appliquer
  `DelegatingSecurityContextAsyncTaskExecutor` pour la deuxième ; passer à une authentification stateless
  (basée sur JWT, pas sur session) ou à un stockage de session partagé pour la troisième.
- **Prévention :** Privilégier l'authentification stateless pour les services mis à l'échelle horizontalement, précisément
  pour éviter la classe de bugs liés aux sticky sessions, et ajouter des tests explicites du comportement d'authentification à travers
  les chemins de code async.

### S7. Les requêtes commencent à échouer avec des erreurs d'épuisement du pool de connexions à la base de données sous charge modérée
- **Symptômes :** Des erreurs comme « connection is not available, request timed out » venant du pool de
  connexions (HikariCP par défaut), corrélées à des périodes de volume de requêtes supérieur à la normale mais
  pas extrême.
- **Diagnostic :** Vérifier si des connexions sont retenues plus longtemps que nécessaire — une cause courante est une
  méthode `@Transactional` qui fait un travail lent non lié à la base (un appel d'API externe) *à l'intérieur* de la
  frontière transactionnelle, retenant une connexion pendant toute son attente sur quelque chose sans rapport.
  Vérifier aussi la taille du pool par rapport à la demande concurrente réelle, et chercher des connexions
  fuitées (une `Connection` gérée manuellement non fermée dans un `finally`/try-with-resources sur
  un chemin d'exception).
- **Exemple :**
  ```java
  @Transactional
  public void placeOrder(Order order) {
      repository.save(order);          // connexion BD acquise pour la transaction
      shippingClient.notify(order);    // appel HTTP externe lent — la connexion reste
                                        // réservée pendant toute sa durée, sans raison
  }

  // Correction : déplacer l'appel externe hors de la frontière transactionnelle.
  public void placeOrder(Order order) {
      saveOrder(order);                // transaction courte — connexion libérée rapidement
      shippingClient.notify(order);    // aucune connexion BD retenue pendant l'attente réseau
  }
  @Transactional
  void saveOrder(Order order) { repository.save(order); }
  ```
- **Résolution :** Déplacer le travail non lié à la base hors de la frontière transactionnelle pour que les connexions ne soient retenues
  que le temps réellement nécessaire, corriger toute fuite de connexion, et dimensionner le pool délibérément (pas
  simplement au plus grand nombre qui « semble sûr ») par rapport à la demande concurrente mesurée.
- **Prévention :** Garder les méthodes `@Transactional` centrées uniquement sur le travail de base de données, et surveiller
  les métriques active/idle/pending du pool de connexions pour que l'épuisement soit visible comme une tendance avant qu'il
  ne devienne une panne.

### S8. Les appels vers un microservice aval échouent occasionnellement, et ces échecs se propagent en cascade jusqu'à faire tomber des parties sans rapport du système
- **Symptômes :** Une dépendance aval devient lente ou instable, et peu après, des fonctionnalités en apparence
  sans rapport dans le service appelant commencent aussi à échouer ou à expirer.
- **Diagnostic :** C'est le schéma classique de défaillance en cascade — les appelants se bloquent en attendant la
  dépendance lente, épuisant un pool de threads partagé (Q21 du module 1) dont dépendent aussi d'autres chemins de requête
  sains, si bien que la lenteur d'une dépendance fait tomber la capacité de tout le reste.
- **Exemple :**
  ```java
  // Aucun timeout configuré du tout — un aval bloqué peut bloquer ce thread indéfiniment.
  public Inventory checkInventory(String sku) {
      return restTemplate.getForObject("/inventory/" + sku, Inventory.class);
  }

  // Correction : un timeout explicite plus un circuit breaker (Q30), pour qu'une dépendance instable
  // échoue vite au lieu d'épuiser le pool de threads partagé de traitement des requêtes.
  RestTemplate client = restTemplateBuilder
      .setConnectTimeout(Duration.ofSeconds(2))
      .setReadTimeout(Duration.ofSeconds(2))
      .build();
  ```
- **Résolution :** Ajouter un circuit breaker (Q30) autour de l'appel précis pour que les échecs y soient
  rapides au lieu d'empiler des threads, ajouter un timeout raisonnable (ne jamais appeler un service aval sans
  aucun timeout), ajouter un retry avec backoff spécifiquement pour les échecs transitoires (pas pour chaque
  échec sans discernement — réessayer un service réellement en panne ne fait qu'ajouter de la charge), et
  isoler le pool de threads utilisé pour cet appel du pool servant les requêtes sans rapport (pattern
  bulkhead) pour que son épuisement ne puisse pas affamer tout le reste.
- **Prévention :** Traiter « que se passe-t-il quand cet appel aval est lent ou en panne » comme une question de
  conception obligatoire pour chaque nouvel appel externe, pas comme une réflexion après coup une fois qu'il cause un incident.

### S9. Des utilisateurs signalent un comportement ancien/périmé pendant un certain temps après le déploiement d'une nouvelle version
- **Symptômes :** Un correctif de bug ou un changement de fonctionnalité est déployé, mais certains utilisateurs signalent que l'ancien comportement
  persiste pendant des minutes à des heures ensuite.
- **Diagnostic :** Distinguer un déploiement progressif (rolling) où anciennes et nouvelles instances servent brièvement le trafic
  simultanément (attendu, temporaire et généralement sans conséquence) d'une véritable couche de cache (CDN,
  en-têtes de cache HTTP, un cache applicatif comme `@Cacheable`) qui sert encore des réponses d'avant le déploiement
  bien après la fin du rollout.
- **Exemple :**
  ```java
  @Cacheable("pricingRules")
  public PricingRule getRule(String sku) { return repository.findRule(sku); }
  // Un correctif de la logique de tarification a été déployé, mais ce cache n'a pas de TTL et rien
  // ne l'évince au déploiement — il continue de servir l'ancien PricingRule pendant des heures.

  // Correction : évincer explicitement chaque fois que la règle sous-jacente change.
  @CacheEvict(value = "pricingRules", allEntries = true)
  public void onPricingRulesChanged() { }
  ```
- **Résolution :** Pour le chevauchement d'un rolling deploy, c'est souvent attendu et cela se résout tout seul — confirmer
  que le rollout est réellement terminé. Pour un problème de cache, soit invalider les clés de cache concernées
  au déploiement, raccourcir le TTL des données qui changent avec les releases, soit ajouter un mécanisme de
  cache-busting (URL versionnées/ETags) lié à la version déployée.
- **Prévention :** Documenter le temps de propagation attendu de chaque couche de cache de la stack pour que « est-ce
  vraiment un bug » ait une réponse rapide, et préférer des TTL courts plus une invalidation explicite à de
  longs TTL pour tout ce qui change avec les déploiements.

### S10. Un scanner de secrets (ou une revue de sécurité) signale des credentials de base de données commités dans `application.properties`
- **Symptômes :** Des mots de passe de base de données, des clés d'API ou d'autres secrets sont trouvés en clair dans un
  fichier properties/YAML versionné.
- **Diagnostic :** C'est un constat simple mais urgent — quiconque a accès au dépôt
  (y compris, pour un dépôt public, tout Internet, plus toute personne l'ayant jamais cloné, puisque l'historique
  git conserve le contenu supprimé) possède le credential.
- **Exemple :**
  ```properties
  # application.properties — commité dans le repo, visible dans chaque clone et chaque
  # commit passé même après avoir été « retiré » de la dernière révision.
  spring.datasource.password=Sup3rSecret!
  ```
  ```bash
  # Faire une rotation immédiatement, puis le sortir entièrement du contrôle de version.
  export SPRING_DATASOURCE_PASSWORD=$(vault kv get -field=password secret/db)
  ```
- **Résolution :** Faire tourner (rotation) immédiatement le credential exposé — le retirer du fichier actuel
  ne suffit pas, puisqu'il reste dans l'historique git. Déplacer les secrets vers des variables d'environnement
  injectées au déploiement, ou vers un gestionnaire de secrets dédié (Vault, AWS Secrets Manager, ou le
  mécanisme de secrets natif de l'orchestrateur), référencés depuis la configuration plutôt qu'embarqués dans
  celle-ci. Nettoyer l'historique git si l'exposition est assez grave pour le justifier (le coordonner
  soigneusement — réécrire l'historique affecte chaque clone).
- **Prévention :** Ajouter un scanner de secrets en pre-commit ou en CI pour que cela ne puisse pas être mergé,
  et traiter « les secrets ne vivent jamais dans le contrôle de version, point final » comme une règle non négociable appliquée
  par des outils, pas seulement par la discipline de la code review.

### S11. Une méthode `@Transactional` échoue en cours de route — que deviennent réellement les changements déjà effectués ?
- **Symptômes :** Une opération en plusieurs étapes dans une transaction (mise à jour de A, puis mise à jour de B, puis B
  échoue) — la question est dans quel état la base de données se retrouve.
- **Diagnostic/explication :** Par défaut, Spring annule *toute* la transaction sur une
  exception unchecked (toute `RuntimeException`) — aucun des changements ne persiste, y compris la
  mise à jour de A réussie plus tôt, car tout le bloc est atomique. Point crucial, Spring n'annule
  **pas** par défaut sur une exception *checked* — cela demande de configurer explicitement
  `@Transactional(rollbackFor = Exception.class)` ou le type checked précis, ce qui est un piège courant
  et dangereux : une équipe suppose que toute exception annule la transaction, puis un chemin d'exception checked
  commite silencieusement une opération à moitié terminée.
- **Exemple :**
  ```java
  @Transactional
  public void transfer(Account from, Account to, BigDecimal amount)
          throws InsufficientFundsException {
      from.debit(amount);
      to.credit(amount);
      if (from.getBalance().signum() < 0) {
          throw new InsufficientFundsException(); // une exception CHECKED
          // Par défaut ceci N'annule PAS — le débit ci-dessus est commité silencieusement,
          // laissant `from` à découvert sans aucune trace correspondante du pourquoi.
      }
  }

  // Correction : être explicite sur les exceptions qui doivent déclencher un rollback.
  @Transactional(rollbackFor = InsufficientFundsException.class)
  public void transfer(...) throws InsufficientFundsException { /* ... */ }
  ```
- **Résolution :** Auditer chaque frontière `@Transactional` pouvant lever une exception checked et
  confirmer explicitement que le comportement de rollback correspond à l'intention, plutôt que de s'appuyer sur le défaut
  réservé aux exceptions unchecked.
- **Prévention :** Mettre par défaut `rollbackFor = Exception.class` sur les nouvelles méthodes transactionnelles sauf
  s'il existe une raison précise et documentée pour qu'une exception checked commite quand même — le
  défaut réservé aux unchecked est un piège qu'il vaut mieux surcharger délibérément à chaque fois.

### S12. Pendant un incident, la sortie de logs attendue est absente ou incomplète en production
- **Symptômes :** Une équipe qui enquête sur un incident constate que les lignes de log précises dont elle a besoin
  (ou même aucun log, sur une fenêtre de temps) ne sont tout simplement pas présentes dans le système d'agrégation de logs.
- **Diagnostic :** Vérifier d'abord le niveau de log configuré dans cet environnement — une cause courante est
  une production tournant en `WARN` ou `ERROR` alors que le détail de diagnostic manquant était journalisé en
  `DEBUG`/`INFO` et n'a jamais été émis. Vérifier aussi les échecs d'acheminement des logs (l'application journalisait bien
  en local, mais le shipper/agent qui transmet les logs à l'agrégateur était lui-même en panne ou saturé) et
  les appenders de logging asynchrones qui peuvent perdre ou retarder des messages sous charge.
- **Exemple :**
  ```yaml
  # config de logging de production — le détail dont l'incident a besoin n'a jamais été émis du tout.
  logging:
    level:
      root: WARN
  ```
  ```bash
  # Monter le logger concerné à chaud, sans redéploiement, pour capturer la prochaine occurrence :
  curl -X POST localhost:8080/actuator/loggers/com.example.orders \
    -H 'Content-Type: application/json' -d '{"configuredLevel": "DEBUG"}'
  ```
- **Résolution :** Utiliser `/actuator/loggers` (Q23) pour passer le logger concerné en `DEBUG` à chaud,
  sans redéploiement, afin de capturer le détail de l'occurrence *suivante* si celle-ci est déjà manquée ;
  corriger le pipeline d'acheminement des logs si c'est là le vrai manque.
- **Prévention :** Mettre `INFO` par défaut en production (pas `WARN`) pour tout ce qui pourrait compter
  pendant un incident, et surveiller le pipeline de logs lui-même (retard d'acheminement, taux de perte) comme sa propre
  métrique de santé — « les logs existent en local mais ne sont jamais arrivés » est sinon invisible jusqu'à ce qu'on en ait
  besoin.

### S13. Le temps de démarrage de l'application a considérablement augmenté, ralentissant les déploiements et l'autoscaling
- **Symptômes :** Un service qui démarrait en quelques secondes prend maintenant 30+ secondes, ce qui
  compte directement pour les déploiements progressifs et pour la réactivité de l'autoscaling lors d'un pic
  de trafic.
- **Diagnostic :** Spring Boot expose un rapport de démarrage (`spring.application.admin.enabled` /
  le rapport d'auto-configuration, ou simplement les logs de démarrage horodatés) montrant quelles
  classes d'auto-configuration et quels beans ont mis le plus de temps à s'initialiser — généralement le vrai
  coupable est un component scanning sur un package inutilement large, un bean eager (non lazy)
  faisant de l'I/O lente au démarrage (préchauffer un cache, pinger chaque dépendance aval), ou simplement des
  dépendances accumulées qui ont entraîné une auto-configuration que personne n'utilise.
- **Exemple :**
  ```
  2026-09-16T10:00:01  Initializing ExecutorService 'applicationTaskExecutor'
  2026-09-16T10:00:14  Warming cache: PricingCacheWarmer  (+13.2s)   <-- the culprit
  2026-09-16T10:00:15  Tomcat started on port 8080
  ```
  ```java
  // Correction : ne pas bloquer le démarrage sur un préchauffage lent et non essentiel.
  @EventListener(ApplicationReadyEvent.class)
  void warmCacheAfterStartup() { pricingCache.warm(); } // s'exécute après que l'app sert déjà
  ```
- **Résolution :** Réduire les packages de base de `@ComponentScan` si le scanning est trop large, différer les
  initialisations réellement lentes (déplacer un préchauffage de cache pour qu'il s'exécute après la fin du démarrage, sans le bloquer), et
  exclure explicitement les classes d'auto-configuration inutilisées.
- **Prévention :** Suivre le temps de démarrage comme une métrique dans le temps en CI, comme on suivrait le temps de build
  ou la taille du bundle, afin qu'une régression soit attrapée dans la PR qui l'a introduite plutôt que
  découverte des mois plus tard sous la forme « c'est devenu un peu lent depuis toujours ».

### S14. Un job de fond de longue durée est parfois tué en pleine exécution pendant un déploiement
- **Symptômes :** Un job batch ou une tâche async qui dure des minutes se retrouve parfois dans un
  état à moitié terminé, en corrélation avec les heures de déploiement.
- **Diagnostic :** C'est une lacune de graceful shutdown — l'orchestrateur qui déploie envoie un signal de terminaison
  à l'ancienne instance, et si l'application n'attend pas que le travail en cours se termine
  (ou ne rejette pas le nouveau travail et ne draine pas d'abord), un job en cours d'exécution est simplement tué avec le
  processus.
- **Exemple :**
  ```java
  @Scheduled(fixedDelay = 60000)
  void runNightlyExport() { exportService.exportAll(); } // pas de checkpointing, pas de drain —
                                                            // un SIGTERM en cours d'exécution le tue simplement
  ```
  ```yaml
  server:
    shutdown: graceful
  spring:
    lifecycle:
      timeout-per-shutdown-phase: 60s
  ```
- **Résolution :** Activer le graceful shutdown (`server.shutdown=graceful` dans Spring Boot récent,
  avec un `spring.lifecycle.timeout-per-shutdown-phase` approprié), et pour les jobs réellement
  de longue durée en particulier, les sortir entièrement du processus de traitement des requêtes vers un
  job runner/consommateur de queue dédié qui peut être drainé indépendamment, avec du checkpointing pour qu'un
  kill forcé reprenne au lieu de repartir de zéro.
- **Prévention :** Traiter « que devient le travail en cours pendant un déploiement » comme une question de conception
  obligatoire pour tout ce qui est de longue durée, de la même façon que S8 traite l'échec d'appel aval comme une
  question obligatoire pour tout ce qui appelle à l'extérieur.

### S15. Un bug traverse plusieurs microservices, et on ne sait pas quel service de la chaîne est réellement responsable
- **Symptômes :** Une erreur ou un problème de latence visible par l'utilisateur se produit clairement quelque part dans une chaîne de
  requêtes multi-services, mais les logs propres de chaque service paraissent anodins pris isolément.
- **Diagnostic :** Sans trace ID partagé propagé à chaque saut, les logs de chaque service sont des
  îlots isolés sans moyen de corréler « cette requête utilisateur précise » entre tous —
  le diagnostic *est* la lacune : le tracing distribué n'est pas en place, ou le contexte de trace n'est pas
  propagé à travers un saut précis (souvent une frontière de message queue, où les en-têtes de trace
  ne se propagent pas automatiquement comme le font les en-têtes HTTP avec la bonne instrumentation).
- **Exemple :**
  ```
  service-a: traceId=abc123 spanId=001  -- HTTP call to service-b, headers propagated
  service-b: (no trace context)         -- consumed from a Kafka message instead,
                                            headers were never carried over into the payload
  # les logs propres de service-b paraissent « propres » isolément — le saut réellement lent/cassé est
  # invisible sans un trace ID reliant entre eux les logs des deux services.
  ```
  ```java
  // Correction : propager le contexte de trace aussi via les métadonnées de message, pas seulement les en-têtes HTTP.
  record OrderEvent(String orderId, String traceId, String spanId) { }
  ```
- **Résolution :** Instrumenter la chaîne avec un standard de tracing (OpenTelemetry, propageant les IDs de trace/
  span via les en-têtes HTTP et, délibérément, via les métadonnées de message pour les sauts async),
  envoyer les traces vers un backend (Jaeger, Zipkin, ou un APM éditeur), et utiliser la trace obtenue pour
  identifier précisément quel saut a introduit la latence ou l'erreur.
- **Prévention :** Faire du tracing distribué une partie de la base de chaque nouveau service dès le premier
  jour, pas quelque chose de rajouté après le premier incident inter-services impossible à
  diagnostiquer — le rajouter de façon cohérente à chaque saut, y compris les sauts async, demande bien plus de
  travail que de le construire dès le départ.

### S16. Un déploiement provoque une rafale de requêtes en échec pendant les quelques secondes autour de l'arrêt de l'ancienne instance
- **Symptômes :** Le taux d'erreurs monte brièvement, spécifiquement pendant chaque déploiement progressif, pour
  les requêtes qui étaient en cours quand une ancienne instance a été terminée.
- **Diagnostic :** L'orchestrateur envoie probablement `SIGTERM` puis un kill brutal peu après,
  sans que l'application n'ait le temps (ou n'utilise le temps) d'arrêter d'accepter de nouvelles connexions, de terminer
  les requêtes en cours et de se désenregistrer du load balancer *avant* que le processus ne se termine réellement.
- **Exemple :**
  ```yaml
  server:
    shutdown: graceful
  # Kubernetes : laisser à l'app le temps de se désenregistrer du service mesh/load balancer
  # AVANT que le SIGTERM qui l'arrête réellement ne soit même envoyé.
  lifecycle:
    preStop:
      exec:
        command: ["sh", "-c", "sleep 5"]
  ```
- **Résolution :** Activer le graceful shutdown de Spring Boot pour que les requêtes en cours puissent
  se terminer avant la sortie de la JVM, s'assurer que le load balancer/service mesh désenregistre l'instance
  *avant* que le trafic ne soit coupé (pas simultanément), et donner à la période de grâce de terminaison de l'orchestrateur
  assez de marge pour que les deux étapes se terminent réellement (un hook `preStop` ajoutant un court délai
  avant `SIGTERM` est un correctif courant spécifique à Kubernetes — voir module 6).
- **Prévention :** Traiter le déploiement sans interruption comme une propriété testée, pas une hypothèse — un
  simple test de charge qui continue d'envoyer du trafic pendant un déploiement et vérifie zéro requête échouée
  attrape immédiatement une régression de graceful shutdown, plutôt qu'elle ne soit découverte comme
  un incident récurrent que personne n'a investigué.

### S17. `LazyInitializationException` apparaît en production juste après un nettoyage « anodin »
- **Symptômes :** Après une release qui a positionné `spring.jpa.open-in-view=false` (pour corriger un avertissement d'épuisement
  du pool, Q17), plusieurs endpoints se mettent à retourner `500` avec
  `org.hibernate.LazyInitializationException: failed to lazily initialize a collection of role
  Order.lines: could not initialize proxy - no Session`. Les tests qui appellent directement le service
  passent tous.
- **Diagnostic :** Le message est précis : quelque chose a touché une association lazy après la fermeture de la session.
  Lire la stack trace de bas en haut : l'accès a lieu dans la couche contrôleur ou dans le
  `BeanSerializer` de Jackson — du code qui ne s'exécutait que parce qu'OSIV gardait la session ouverte pour toute la
  requête. Les tests unitaires du service passent car ils ne sérialisent jamais le résultat. Lister chaque
  entité qui sort d'une méthode de service et chaque collection lazy qu'elle expose ; chacune est soit un
  fetch manquant, soit une fuite de conception.
- **Exemple :**
  ```java
  @Transactional(readOnly = true)
  public Order find(long id) { return orders.findById(id).orElseThrow(); } // lines = proxy lazy

  @GetMapping("/orders/{id}")
  Order get(@PathVariable long id) {
      return service.find(id);        // Jackson parcourt order.getLines() -> pas de Session -> boom
  }
  ```
- **Résolution :** Ne **pas** réactiver OSIV ni passer l'association en `EAGER` (cela ne fait que
  figer un N+1, Q18). Charger ce dont la réponse a besoin *dans* le service, et retourner un DTO :
  ```java
  @Query("select new com.acme.OrderView(o.id, o.status, l.sku, l.qty) " +
         "from Order o join o.lines l where o.id = :id")
  List<OrderRow> findRows(long id);          // ou @EntityGraph(attributePaths = "lines")
  ```
  Vérifier avec un test au niveau contrôleur (`@WebMvcTest`/`MockMvc` ou `@SpringBootTest`) qui vérifie
  le corps JSON et compte les requêtes SQL (statistics Hibernate ou un datasource-proxy) — le
  nombre doit être constant, pas proportionnel à `lines`.
- **Prévention :** Ne jamais retourner d'entités depuis les contrôleurs ; ajouter un test d'intégration par endpoint
  (sérialisation incluse) ; garder OSIV désactivé dès le début d'un projet — le rajouter après coup est bien plus
  pénible que de commencer sans.

### S18. Chaque job planifié s'exécute une fois par replica, donc les clients reçoivent des emails en double et sont débités deux fois
- **Symptômes :** Après le passage de 1 à 3 pods, le job nocturne « send invoices » envoie chaque
  client trois fois par email ; un job de facturation mensuelle débite certains comptes deux fois. Les logs montrent le même
  job démarrant à la même seconde sur chaque pod.
- **Diagnostic :** `@Scheduled` est *local à une JVM* : chaque instance a son propre scheduler et ne sait
  rien des autres, donc N replicas signifie N exécutions. Le confirmer en grepant les logs pour la
  ligne de démarrage du job sur les pods avec des timestamps identiques. Cela est passé inaperçu auparavant parce qu'il y
  avait exactement une instance (ou parce que le job était accidentellement idempotent).
- **Exemple :**
  ```java
  @Scheduled(cron = "0 0 2 * * *")
  void sendInvoices() { invoiceService.sendAllPending(); }   // s'exécute sur CHAQUE pod à 02:00
  ```
- **Résolution :** Faire en sorte qu'exactement une instance gagne à chaque exécution. Options, par ordre de préférence : un
  `CronJob` Kubernetes (la plateforme garantit une exécution ; le job est un processus séparé), un
  verrou distribué avec **ShedLock** (une ligne dans une table existante ou une clé Redis acquise à chaque exécution),
  ou un advisory lock PostgreSQL. Avec ShedLock :
  ```java
  @Scheduled(cron = "0 0 2 * * *")
  @SchedulerLock(name = "sendInvoices", lockAtMostFor = "30m", lockAtLeastFor = "1m")
  void sendInvoices() { invoiceService.sendAllPending(); }
  ```
  `lockAtMostFor` protège contre un détenteur planté qui garderait le verrou indéfiniment ;
  `lockAtLeastFor` empêche un job rapide d'être relancé par un replica dont l'horloge est un peu en retard.
  Rendre aussi le job lui-même **idempotent** (marquer chaque facture `SENT` dans la même transaction, ou
  utiliser une clé unique) puisqu'un timeout de verrou ou un redémarrage de pod peut encore provoquer une double exécution rare
  (module 4 Q13). Vérifier en lançant trois replicas en local et en vérifiant une exécution par
  déclenchement.
- **Prévention :** Traiter « combien d'instances exécutent ceci ? » comme une question obligatoire pour chaque
  méthode `@Scheduled` en code review ; tenir un inventaire des jobs planifiés avec nom du verrou, durée
  max et notes d'idempotence.

### S19. Des commandes disparaissent alors que le code a « géré » l'exception et retourné un succès
- **Symptômes :** Le support signale des clients qui ont obtenu une page de confirmation mais n'ont aucune commande. Les logs
  montrent `WARN audit failed, continuing` suivi quelques millisecondes plus tard par
  `UnexpectedRollbackException: Transaction silently rolled back because it has been marked as
  rollback-only`. Parfois l'utilisateur voit un `500` et parfois un succès — selon que
  quelque chose en amont a aussi avalé l'exception.
- **Diagnostic :** Trouver la méthode `@Transactional` externe et chercher un `try/catch` autour d'un appel
  vers *un autre* bean `@Transactional`. La méthode interne a levé une exception, son proxy a marqué la transaction
  partagée (`REQUIRED`) rollback-only, la méthode externe a intercepté l'exception et est retournée
  normalement, et le commit a refusé de se poursuivre (Q15). Activer
  `logging.level.org.springframework.transaction=DEBUG` (ou `TRACE`) pour voir « Participating in
  existing transaction » suivi de « Setting JPA transaction on EntityManager rollback-only ».
- **Exemple :**
  ```java
  @Transactional
  public void place(Order o) {
      orders.save(o);
      try { notifier.publish(o); }               // notifier.publish est @Transactional (REQUIRED)
      catch (RuntimeException e) { log.warn("audit failed, continuing", e); }
  }   // commit -> UnexpectedRollbackException, commande disparue
  ```
- **Résolution :** Décider ce que veut le *métier*. Si l'effet de bord ne doit pas affecter la
  commande, l'exécuter indépendamment : `@Transactional(propagation = REQUIRES_NEW)` sur la méthode interne,
  ou mieux le déplacer *après* le commit avec un `@TransactionalEventListener` (Q34) — un outbox s'il
  ne doit pas être perdu. S'il fait *partie* de la commande, ne pas intercepter l'exception. Ajouter un test qui
  fait lever une exception au collaborateur et vérifie que l'état final de la commande correspond à la
  sémantique voulue.
- **Prévention :** Règle d'équipe : ne jamais intercepter une exception runtime levée par un appel qui franchit une
  frontière de bean transactionnel sans savoir si la transaction est maintenant rollback-only ;
  préférer des attributs de propagation explicites sur les services d'effets de bord plutôt que de s'en remettre au défaut.

### S20. Les threads s'accumulent et le service cesse de répondre parce qu'une dépendance a cessé de répondre
- **Symptômes :** Une API d'inventaire aval se met à se bloquer (elle accepte les connexions mais ne
  répond jamais). En une minute tous les threads Tomcat (200 par défaut) sont occupés, `/actuator/health`
  expire, le pod est redémarré par la liveness probe, et le nouveau pod meurt de la même façon.
  Le CPU est au repos ; le dashboard de la dépendance ne montre aucune erreur — seulement *aucune réponse*.
- **Diagnostic :** Un thread dump (`jcmd <pid> Thread.print`) montre les threads de requête tous parqués
  dans `SocketInputStream.socketRead0` / `SocketOrChannelRead` sous des appels bloquants `RestTemplate.exchange` ou
  `WebClient`. Vérifier la configuration du client : un `RestTemplate` construit avec
  `new RestTemplate()` utilise `SimpleClientHttpRequestFactory` **sans** timeout de connexion ni de lecture,
  et le `WebClient` de Reactor Netty n'a pas de timeout de réponse par défaut, donc un pair bloqué retient le thread
  aussi longtemps qu'il le veut. Une seule dépendance non bornée a consommé tout le pool de threads servlet,
  ce qui explique pourquoi des endpoints sans rapport ont aussi échoué.
- **Exemple :**
  ```java
  RestTemplate rt = new RestTemplate();                 // aucun timeout du tout
  Stock s = rt.getForObject("http://inventory/stock/{sku}", Stock.class, sku); // peut bloquer indéfiniment
  ```
- **Résolution :** Définir des timeouts explicites sur chaque client sortant, dimensionnés d'après le SLO de latence
  de la dépendance, et envelopper l'appel dans un circuit breaker avec un bulkhead pour qu'une dépendance ne puisse pas
  prendre tous les threads (Q30, S8) :
  ```java
  var f = new SimpleClientHttpRequestFactory();
  f.setConnectTimeout(2_000);   // ms
  f.setReadTimeout(3_000);
  RestTemplate rt = new RestTemplate(f);

  // WebClient: HttpClient.create().responseTimeout(Duration.ofSeconds(3)) + .timeout(...) on the Mono
  ```
  Vérifier avec un test d'injection de panne (un stub qui dort 30 s) : l'appelant doit échouer en ~3 s,
  le breaker doit s'ouvrir, et les endpoints sans rapport doivent rester sains. Séparer aussi liveness de
  readiness pour qu'une dépendance lente ne fasse pas tuer le pod.
- **Prévention :** Des beans builder `RestTemplate`/`WebClient` centraux avec timeouts obligatoires (interdire
  `new RestTemplate()` via ArchUnit), un bulkhead par dépendance, et un dashboard des appels
  sortants en cours et de leur p99.

### S21. Un service WebFlux est moins performant que l'ancien service MVC, et la latence explose pour tout le monde en même temps
- **Symptômes :** Après la migration d'un service vers Spring WebFlux « pour la scalabilité », le débit est
  plus bas qu'avant ; sous charge modérée, *toutes* les requêtes se bloquent ensemble pendant des centaines de millisecondes.
  Il n'existe que quelques threads, et ils sont tous occupés.
- **Diagnostic :** WebFlux tourne sur un minuscule ensemble fixe de threads d'event loop (environ un par cœur de
  CPU). Un seul appel bloquant — JDBC, un client HTTP bloquant, `Thread.sleep`, `.block()`,
  un calcul CPU lourd — empêche cet event loop de servir *toutes* les autres connexions qui lui sont assignées. Un
  thread dump montre les threads `reactor-http-nio-*` dans du code JDBC ou de lecture de socket. Utiliser
  BlockHound en test ou en staging (`BlockHound.install()`), qui lève une exception à l'appel bloquant
  exact.
- **Exemple :**
  ```java
  @GetMapping("/users/{id}")
  Mono<User> get(@PathVariable long id) {
      return Mono.just(jdbcTemplate.queryForObject(SQL, mapper, id)); // bloque l'event loop
  }
  ```
- **Résolution :** Soit passer entièrement en réactif (R2DBC, `WebClient`), soit déplacer explicitement le
  travail bloquant inévitable hors de l'event loop :
  ```java
  return Mono.fromCallable(() -> jdbcTemplate.queryForObject(SQL, mapper, id))
             .subscribeOn(Schedulers.boundedElastic());
  ```
  Puis se demander si WebFlux était le bon choix : avec une stack JDBC bloquante, Spring MVC
  sur virtual threads offre la concurrence sans le modèle de programmation réactive (module 1
  Q24). Vérifier avec un test de charge comparant le p99 avant/après et BlockHound au vert en CI.
- **Prévention :** Ne choisir le réactif que lorsque *tout* le chemin (driver inclus) est non bloquant ;
  exécuter BlockHound dans la suite de tests d'intégration ; documenter sur quel thread s'exécute chaque couche.

### S22. Les emails « Welcome » cessent silencieusement d'être envoyés, et la mémoire grimpe, alors que l'API retourne un succès
- **Symptômes :** L'endpoint d'inscription retourne `201` comme toujours, mais une part croissante des nouveaux utilisateurs
  ne reçoit jamais l'email de bienvenue ; rien n'apparaît dans les dashboards ni à l'astreinte. L'usage du heap sur les pods
  grimpe régulièrement sur plusieurs jours.
- **Diagnostic :** L'envoi est une méthode `void @Async`, donc son résultat est invisible pour l'appelant.
  Chercher dans les logs `Unexpected exception occurred invoking async method` trouve des milliers de
  `MailSendException` — le fournisseur de mail rejetait les requêtes depuis des jours, et l'
  `AsyncUncaughtExceptionHandler` par défaut ne fait que journaliser. La croissance du heap est la file
  effectivement non bornée de l'executor qui se remplit de tâches sans retry (Q21) ; un histogramme du heap montre
  des files de `ThreadPoolExecutor$Worker` pleines de `Runnable`s référençant des objets `User`.
- **Exemple :**
  ```java
  @Async
  public void sendWelcome(User user) { mailClient.send(user.email(), template); } // échec -> ligne de log
  ```
- **Résolution :** Rendre l'échec visible et borné. Utiliser un executor nommé et borné avec une
  politique de rejet ; retourner `CompletableFuture<Void>` et attacher des handlers `exceptionally`, ou (pour
  un email « à envoyer absolument ») ne pas l'envoyer en ligne du tout — écrire une ligne dans une table outbox dans la transaction
  d'inscription et laisser un worker la livrer avec retry/backoff et un état dead-letter (module 4
  Q26/Q9). Enregistrer un `AsyncConfigurer#getAsyncUncaughtExceptionHandler` qui incrémente une
  métrique et déclenche une alerte. Vérifier en pointant le client mail vers un stub qui échoue : le compteur d'échecs
  doit alerter, la file doit rester bornée, et aucune requête d'inscription ne doit être affectée.
- **Prévention :** Des métriques pour chaque frontière asynchrone (en file, en cours, échoué, rejeté) ;
  une alerte sur le taux d'échec ; un choix explicite, pour chaque effet de bord, entre « best effort » et
  « ne doit pas être perdu ».

## 📌 Cheat-sheet

- **DI** = la classe déclare ses besoins, le conteneur les fournit → couplage faible, testabilité, pas de `new` fait main.
- **Design patterns dans Spring** : DI/IoC (injection), Singleton (scope par défaut), Factory (`ApplicationContext`), Strategy (injection multi-implémentations), Proxy (`@Transactional`, sécurité, AOP), Template (`JdbcTemplate`).
- **`@Transactional` en auto-invocation et sur méthodes private** = no-op silencieux, car basé sur les proxies — corriger via self-injection, un autre bean, ou le weaving AspectJ.
- **`flush()` ≠ `commit()`** — flush synchronise avec la BD plus tôt, ne termine pas la transaction.
- **Scopes de beans** : `singleton` = une instance partagée (champs d'instance mutables = bug d'état partagé entre requêtes) ; `prototype`/`request`/`session` ont des portées différentes.
- **Injection par constructeur > injection par champ** : immuable, explicite, testable sans conteneur.
- **Dépendances circulaires** : résolubles pour l'injection par setter/champ (cache de références anticipées), *pas* pour l'injection purement par constructeur — échec immédiat au démarrage à la place.
- **`@Async` perd le contexte de sécurité** par défaut — utiliser `DelegatingSecurityContextAsyncTaskExecutor`.
- **Proxy JDK** nécessite une interface ; **CGLIB** sous-classe mais ne peut pas proxifier les classes/méthodes `final` — AOP silencieusement ignoré dans les deux cas si violé.
- **Actuator** : exposer `health`/`info`/`metrics`/`loggers` à l'extérieur si besoin ; ne jamais exposer `env`/`beans`/`heapdump` publiquement.
- **Précédence de la config** (haut→bas) : arguments CLI → variables d'env → fichier spécifique au profil → fichier de base → valeurs par défaut du code.
- **`@ControllerAdvice`** centralise le mapping exception→statut HTTP ; ne jamais divulguer de stack traces aux clients.
- **CORS** : origine wildcard + `allowCredentials(true)` est rejeté — doit être une allow-list explicite.
- **Organisation hexagonale** : `domain` (aucune dépendance framework) → `application` (use cases + ports) → `infrastructure` (adapters) ; imposer avec ArchUnit.
- **Circuit breaker** (Resilience4j) : échouer vite sur une dépendance instable au lieu d'empiler des threads en attente — empêche la défaillance en cascade.
- **`@Transactional` annule sur les exceptions unchecked par défaut, PAS les checked** — définir `rollbackFor` explicitement.
- **Requêtes N+1** : associations lazy récupérées dans une boucle → 1+N requêtes ; corriger avec un `JOIN FETCH`/entity graph spécifique à la requête, pas un fetch type `EAGER` global.
- **`@Cacheable` + valeur de retour mutable** : le cache stocke la référence, pas une copie — un appelant qui modifie une `List`/DTO en cache corrompt tous les futurs cache hits.
- **`@Valid` ne se propage pas** : un champ objet imbriqué a besoin de sa propre annotation `@Valid`, sinon ses contraintes ne sont silencieusement jamais vérifiées.
- **Graceful shutdown** : `server.shutdown=graceful` + période de grâce de l'orchestrateur, pour que les requêtes en cours se terminent et que le LB désenregistre avant la sortie du processus.
- **`@Configuration` vs `@Component` avec `@Bean`** : le full mode (CGLIB) fait retourner le singleton aux appels inter-`@Bean` ; le lite mode / `proxyBeanMethods = false` crée une nouvelle instance à chaque appel — prendre les dépendances en paramètres de méthode.
- **`@ConfigurationProperties` plutôt que `@Value`** pour les paramètres groupés : typé, relaxed binding, `@Validated` fail-fast au démarrage, métadonnées IDE.
- **Propagation** : `REQUIRED` partage une transaction — une exception runtime interne la marque rollback-only même si l'appelant l'intercepte (`UnexpectedRollbackException`) ; `REQUIRES_NEW` = transaction indépendante mais une seconde connexion du pool. `readOnly = true` est un indice, pas un garde-fou d'écriture.
- **Défauts de `@Scheduled`/`@Async`** : un seul thread de scheduler ; l'executor `@Async` de Boot a une file non bornée (Spring classique : un nouveau thread par tâche) ; les échecs de `void @Async` n'atteignent jamais l'appelant — utiliser un executor nommé et borné + un handler d'échec.
- **Open-in-View** : commodité qui retient un persistence context (et souvent une connexion) pour toute la requête et masque les N+1 — le désactiver, récupérer dans le service, retourner des DTOs.
- **Multi-tenancy** : DB-per-tenant (isolation) → schema-per-tenant → `tenant_id` + row-level security (densité) ; propager le tenant comme le `SecurityContext`, l'inclure dans les clés de cache, migrer chaque tenant.
- **`@TransactionalEventListener(AFTER_COMMIT)`** : ne s'exécute qu'au commit, mais hors de la transaction et non durable — utiliser un outbox pour les événements qui ne doivent pas être perdus.
- **Autorisation** : règles d'URL (la première qui correspond gagne, deny by default en dernier) pour le périmètre ; `@PreAuthorize` sur les services pour rôle/propriété (IDOR) — les limites des proxies s'appliquent (auto-invocation, `private`).
- **`@Scheduled` sur N replicas = N exécutions** : utiliser un `CronJob` K8s, ShedLock ou un advisory lock, et rendre le job idempotent.
- **Les appels sortants ont besoin de timeouts** : `new RestTemplate()` / `WebClient` par défaut peut bloquer indéfiniment et vider le pool servlet — définir des timeouts de connexion/lecture, ajouter un breaker + bulkhead.
- **WebFlux + appel bloquant** = event loop bloqué ; utiliser BlockHound, `boundedElastic`, ou rester sur MVC + virtual threads.
