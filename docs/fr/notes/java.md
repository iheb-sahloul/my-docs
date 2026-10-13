# Java

## JVM & outillage

### Changer de version de JDK (SDKMAN)

```bash
sdk list java
sdk install java 21.0.4-tem
sdk use java 21.0.4-tem      # shell courant uniquement
sdk default java 21.0.4-tem
```

### Lancer un programme en un seul fichier (sans javac, Java 11+)

```bash
java Hello.java
```

### Test rapide avec JShell

```bash
jshell
jshell> List.of(1, 2, 3).stream().map(i -> i * 2).toList()
```

### Thread dump / heap dump d'une JVM en cours d'exécution

```bash
jps -l                                   # trouver le PID
jcmd <pid> Thread.print > threads.txt
jcmd <pid> GC.heap_dump /tmp/heap.hprof
```

### Inspecter une JVM en cours d'exécution avec jcmd

```bash
jcmd <pid> help                          # lister les commandes disponibles
jcmd <pid> VM.flags                      # flags JVM effectifs
jcmd <pid> VM.system_properties
jcmd <pid> GC.class_histogram | head -20 # plus gros consommateurs de mémoire par classe
```

### Flags JVM utiles

```bash
java -Xms512m -Xmx2g \
     -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp \
     -jar app.jar

# en conteneur : dimensionner le heap depuis la limite mémoire au lieu de -Xmx
java -XX:MaxRAMPercentage=75 -jar app.jar
```

### GraalVM native image

```bash
sdk install java <version-graalvm>         # choisir un JDK GraalVM, puis :
native-image --version

# Spring Boot 3
mvn -Pnative native:compile                # exécutable dans target/   (Gradle : ./gradlew nativeCompile)
mvn -Pnative spring-boot:build-image       # image de conteneur via Buildpacks (Gradle : ./gradlew bootBuildImage)
mvn -PnativeTest test                      # exécuter les tests en image native (Gradle : ./gradlew nativeTest)

# générer la config réflexion/ressources en exerçant l'application sur la JVM
java -agentlib:native-image-agent=config-output-dir=src/main/resources/META-INF/native-image -jar app.jar

# comparer avec la JVM
ps -o rss= -p <pid>                        # mémoire résidente (Ko)
```

Pourquoi c'est léger : ni JIT, ni métadonnées de classes, ni profileur à l'exécution, code mort supprimé au build, état
initialisé au build. Compromis : débit maximal inférieur sauf avec la PGO. Détails : [Java Core & JVM](../interviews/java-core-jvm.md) Q39-Q40.

### Logs du GC

```bash
java -Xlog:gc*:file=gc.log:time,uptime,level,tags:filecount=5,filesize=10M -jar app.jar
```

### Java Flight Recorder

```bash
# sur une JVM en cours d'exécution
jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr

# depuis le démarrage
java -XX:StartFlightRecording=duration=60s,filename=rec.jfr -jar app.jar

# aperçu rapide sans JDK Mission Control
jfr print --events jdk.GarbageCollection rec.jfr
```

### Débogage à distance

```bash
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005 -jar app.jar
```

Les commandes de build (lancer un test, ignorer les tests, arbre des dépendances, multi-modules) sont dans [Maven & Gradle](maven-gradle.md).

## Langage & API

### Collections immuables

```java
List<String> names = List.of("a", "b");                 // immuable, refuse les null
Map<String, Integer> ages = Map.of("Ann", 30, "Bob", 25); // jusqu'à 10 paires
Map<String, Integer> more = Map.ofEntries(Map.entry("Ann", 30), Map.entry("Bob", 25));
List<String> snapshot = List.copyOf(mutableList);        // copie immuable

stream.toList();                     // non modifiable (Java 16+)
stream.collect(Collectors.toList()); // mutabilité non garantie
```

### Aide-mémoire des Collectors

```java
import static java.util.stream.Collectors.*;

Map<Status, List<Order>> byStatus = orders.stream().collect(groupingBy(Order::status));
Map<Status, Long> countByStatus   = orders.stream().collect(groupingBy(Order::status, counting()));
Map<Boolean, List<Order>> split   = orders.stream().collect(partitioningBy(Order::isPaid));

// la fonction de fusion évite une IllegalStateException sur les clés en double
Map<String, Order> byId = orders.stream().collect(toMap(Order::id, Function.identity(), (a, b) -> b));

String csv = names.stream().collect(joining(", ", "[", "]"));
```

### Blocs de texte

```java
String json = """
    {
      "id": %d,
      "name": "%s"
    }
    """.formatted(id, name);
```

### Utilitaires String

```java
"  ".isBlank();              // true (isEmpty() vaut false)
" hi ".strip();         // "hi", gère Unicode contrairement à trim()
"ab".repeat(3);              // "ababab"
"a\nb\nc".lines().count();   // 3
"Hello %s".formatted(name);
```

### java.time

```java
Instant now = Instant.now();                                  // un instant (UTC), à stocker
ZonedDateTime paris = now.atZone(ZoneId.of("Europe/Paris"));  // pour l'affichage
LocalDate birthday = LocalDate.of(1990, 5, 17);               // date sans fuseau
Duration timeout = Duration.ofSeconds(30);                    // durée basée sur le temps
Period age = Period.between(birthday, LocalDate.now());       // durée basée sur les dates

LocalDate parsed = LocalDate.parse("17/05/1990", DateTimeFormatter.ofPattern("dd/MM/yyyy"));
String iso = DateTimeFormatter.ISO_INSTANT.format(now);
```

### Records + pattern matching (Java 21)

```java
record Point(int x, int y) {}

String describe(Object o) {
    return switch (o) {
        case Point(int x, int y) when x == y -> "diagonal";
        case Point p -> "point " + p;
        default -> "unknown";
    };
}
```

### Interfaces scellées + switch exhaustif (Java 21)

```java
sealed interface Shape permits Circle, Square {}
record Circle(double r) implements Shape {}
record Square(double side) implements Shape {}

double area(Shape s) {
    return switch (s) {   // pas de default : ajouter un nouveau Shape casse le build ici
        case Circle c -> Math.PI * c.r() * c.r();
        case Square sq -> sq.side() * sq.side();
    };
}
```

### Collections séquencées (Java 21)

```java
List<Integer> list = List.of(1, 2, 3);
list.getFirst();    // 1
list.getLast();     // 3
list.reversed();    // [3, 2, 1] (une vue)

LinkedHashMap<String, Integer> map = new LinkedHashMap<>();
map.firstEntry();
map.pollLastEntry();
```

### Threads virtuels (Java 21)

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i -> executor.submit(() -> fetch(i)));
}
```

### CompletableFuture : combiner, timeout, repli

```java
var user   = CompletableFuture.supplyAsync(() -> userClient.get(id), executor);
var orders = CompletableFuture.supplyAsync(() -> orderClient.list(id), executor);

Dashboard dashboard = user.thenCombine(orders, Dashboard::new)
        .orTimeout(2, TimeUnit.SECONDS)
        .exceptionally(e -> Dashboard.empty())
        .join();

// attendre une liste de futures
CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new)).join();
```

### HttpClient : GET simple (Java 11+)

```java
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder(URI.create("https://api.github.com/users/octocat"))
        .header("Accept", "application/json")
        .timeout(Duration.ofSeconds(5))
        .build();

HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.statusCode() + " " + response.body());
```
