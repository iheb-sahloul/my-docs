# Java

## JVM & tooling

### Switch JDK version (SDKMAN)

```bash
sdk list java
sdk install java 21.0.4-tem
sdk use java 21.0.4-tem      # current shell only
sdk default java 21.0.4-tem
```

### Run a single-file program (no javac, Java 11+)

```bash
java Hello.java
```

### JShell quick test

```bash
jshell
jshell> List.of(1, 2, 3).stream().map(i -> i * 2).toList()
```

### Thread dump / heap dump of a running JVM

```bash
jps -l                                   # find the PID
jcmd <pid> Thread.print > threads.txt
jcmd <pid> GC.heap_dump /tmp/heap.hprof
```

### Inspect a running JVM with jcmd

```bash
jcmd <pid> help                          # list available commands
jcmd <pid> VM.flags                      # effective JVM flags
jcmd <pid> VM.system_properties
jcmd <pid> GC.class_histogram | head -20 # top memory consumers by class
```

### Useful JVM flags

```bash
java -Xms512m -Xmx2g \
     -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp \
     -jar app.jar

# in containers: size the heap from the memory limit instead of -Xmx
java -XX:MaxRAMPercentage=75 -jar app.jar
```

### GraalVM native image

```bash
sdk install java <graalvm-version>         # pick a GraalVM JDK, then:
native-image --version

# Spring Boot 3
mvn -Pnative native:compile                # executable in target/   (Gradle: ./gradlew nativeCompile)
mvn -Pnative spring-boot:build-image       # container image via Buildpacks (Gradle: ./gradlew bootBuildImage)
mvn -PnativeTest test                      # run the tests as a native image (Gradle: ./gradlew nativeTest)

# generate reflection/resource config by exercising the app on the JVM
java -agentlib:native-image-agent=config-output-dir=src/main/resources/META-INF/native-image -jar app.jar

# compare against the JVM
ps -o rss= -p <pid>                        # resident memory (KB)
```

Why it's lean: no JIT, class metadata or profiler at runtime, dead code removed at build time, state initialised at
build time. Trade-off: lower peak throughput unless you use PGO. Details: [Java Core & JVM](../interviews/java-core-jvm.md) Q39-Q40.

### GC logs

```bash
java -Xlog:gc*:file=gc.log:time,uptime,level,tags:filecount=5,filesize=10M -jar app.jar
```

### Java Flight Recorder

```bash
# on a running JVM
jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr

# from startup
java -XX:StartFlightRecording=duration=60s,filename=rec.jfr -jar app.jar

# quick look without JDK Mission Control
jfr print --events jdk.GarbageCollection rec.jfr
```

### Remote debug

```bash
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005 -jar app.jar
```

Build commands (run one test, skip tests, dependency tree, multi-module) live in [Maven & Gradle](maven-gradle.md).

## Language & APIs

### Immutable collections

```java
List<String> names = List.of("a", "b");                 // immutable, rejects nulls
Map<String, Integer> ages = Map.of("Ann", 30, "Bob", 25); // up to 10 pairs
Map<String, Integer> more = Map.ofEntries(Map.entry("Ann", 30), Map.entry("Bob", 25));
List<String> snapshot = List.copyOf(mutableList);        // immutable copy

stream.toList();                     // unmodifiable (Java 16+)
stream.collect(Collectors.toList()); // mutability not guaranteed
```

### Collectors cheat sheet

```java
import static java.util.stream.Collectors.*;

Map<Status, List<Order>> byStatus = orders.stream().collect(groupingBy(Order::status));
Map<Status, Long> countByStatus   = orders.stream().collect(groupingBy(Order::status, counting()));
Map<Boolean, List<Order>> split   = orders.stream().collect(partitioningBy(Order::isPaid));

// merge function avoids IllegalStateException on duplicate keys
Map<String, Order> byId = orders.stream().collect(toMap(Order::id, Function.identity(), (a, b) -> b));

String csv = names.stream().collect(joining(", ", "[", "]"));
```

### Text blocks

```java
String json = """
    {
      "id": %d,
      "name": "%s"
    }
    """.formatted(id, name);
```

### String helpers

```java
"  ".isBlank();              // true (isEmpty() is false)
" hi ".strip();         // "hi", Unicode-aware unlike trim()
"ab".repeat(3);              // "ababab"
"a\nb\nc".lines().count();   // 3
"Hello %s".formatted(name);
```

### java.time

```java
Instant now = Instant.now();                                  // a point in time (UTC), store this
ZonedDateTime paris = now.atZone(ZoneId.of("Europe/Paris"));  // for display
LocalDate birthday = LocalDate.of(1990, 5, 17);               // date without a zone
Duration timeout = Duration.ofSeconds(30);                    // time-based amount
Period age = Period.between(birthday, LocalDate.now());       // date-based amount

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

### Sealed interfaces + exhaustive switch (Java 21)

```java
sealed interface Shape permits Circle, Square {}
record Circle(double r) implements Shape {}
record Square(double side) implements Shape {}

double area(Shape s) {
    return switch (s) {   // no default: adding a new Shape breaks the build here
        case Circle c -> Math.PI * c.r() * c.r();
        case Square sq -> sq.side() * sq.side();
    };
}
```

### Sequenced collections (Java 21)

```java
List<Integer> list = List.of(1, 2, 3);
list.getFirst();    // 1
list.getLast();     // 3
list.reversed();    // [3, 2, 1] (a view)

LinkedHashMap<String, Integer> map = new LinkedHashMap<>();
map.firstEntry();
map.pollLastEntry();
```

### Virtual threads (Java 21)

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    IntStream.range(0, 10_000).forEach(i -> executor.submit(() -> fetch(i)));
}
```

### CompletableFuture: combine, timeout, fallback

```java
var user   = CompletableFuture.supplyAsync(() -> userClient.get(id), executor);
var orders = CompletableFuture.supplyAsync(() -> orderClient.list(id), executor);

Dashboard dashboard = user.thenCombine(orders, Dashboard::new)
        .orTimeout(2, TimeUnit.SECONDS)
        .exceptionally(e -> Dashboard.empty())
        .join();

// wait for a list of futures
CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new)).join();
```

### HttpClient one-shot GET (Java 11+)

```java
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder(URI.create("https://api.github.com/users/octocat"))
        .header("Accept", "application/json")
        .timeout(Duration.ofSeconds(5))
        .build();

HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.statusCode() + " " + response.body());
```
