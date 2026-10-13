# Maven et Gradle

## Maven

### Cycle de vie

Exécuter une phase exécute toutes les phases précédentes du même cycle de vie.

| Phase | Ce qui se passe |
|---|---|
| `validate` | Vérifie que le projet est correct |
| `compile` | Compile `src/main` |
| `test` | Exécute les tests unitaires (Surefire) |
| `package` | Construit le jar/war dans `target/` |
| `verify` | Exécute les tests d'intégration / vérifications (Failsafe) |
| `install` | Copie l'artefact dans `~/.m2` |
| `deploy` | Envoie vers un dépôt distant |

`clean` appartient à un cycle de vie distinct : il ne fait que supprimer `target/`.

```bash
mvn clean package
mvn clean verify
mvn clean install -DskipTests
mvn compile                                    # retour rapide
```

### Options courantes

| Option | Effet |
|---|---|
| `-DskipTests` | Compile les tests mais ne les exécute pas |
| `-Dmaven.test.skip=true` | Ne compile même pas les tests |
| `-o` | Mode hors ligne |
| `-q` | Silencieux |
| `-e` / `-X` | Affiche les stack traces / la sortie de debug complète |
| `-U` | Force la mise à jour des snapshots et des releases manquantes |
| `-T 1C` | Un thread par cœur CPU (build parallèle) |
| `-P prod` | Active un profil |
| `-pl mod -am` | Construit le module + ses dépendances |
| `-rf :mod` | Reprend le build à partir d'un module |
| `-fae` / `-ff` | Échoue à la fin / échoue immédiatement |
| `-Dkey=value` | Définit une propriété |

### Exécuter les tests

```bash
mvn test -Dtest=OrderServiceTest               # une classe
mvn test -Dtest=OrderServiceTest#shouldRefund  # une méthode
mvn test -Dtest='Order*Test,!*IT'              # motifs
mvn verify -Dit.test=PaymentIT                 # test d'intégration Failsafe
mvn test -Dsurefire.failIfNoSpecifiedTests=false -pl api -Dtest=Foo   # module sans ce test
mvn test -DargLine="-Xmx1g -Dspring.profiles.active=test"
mvn surefire-report:report                     # rapport HTML dans target/site
```

### Arbre de dépendances et analyse

```bash
mvn dependency:tree
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core
mvn dependency:tree -Dverbose                  # affiche les doublons/conflits omis
mvn dependency:analyze                         # déclarées inutilisées / utilisées non déclarées
mvn dependency:resolve -Dclassifier=sources
mvn dependency:copy-dependencies -DoutputDirectory=target/lib
mvn help:effective-pom                         # POM après parents + profils
```

```text
[INFO] com.acme:order-service:jar:1.0.0
[INFO] +- org.springframework.boot:spring-boot-starter-web:jar:3.3.2:compile
[INFO] |  +- com.fasterxml.jackson.core:jackson-databind:jar:2.17.2:compile
[INFO] |  |  \- com.fasterxml.jackson.core:jackson-core:jackson-core:2.17.2:compile
```

### Corriger un conflit de versions

```xml
<!-- Fixer une version pour tout le projet, y compris les usages transitifs -->
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>com.fasterxml.jackson</groupId>
      <artifactId>jackson-bom</artifactId>
      <version>2.17.2</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>

<!-- Ou exclure une dépendance transitive -->
<dependency>
  <groupId>org.example</groupId>
  <artifactId>lib</artifactId>
  <version>1.0</version>
  <exclusions>
    <exclusion>
      <groupId>commons-logging</groupId>
      <artifactId>commons-logging</artifactId>
    </exclusion>
  </exclusions>
</dependency>
```

Maven résout les conflits selon « la définition la plus proche l'emporte », puis la première déclarée. Il ne choisit pas la version la plus élevée.

### Scopes de dépendances

| Scope | Compilation | Test | Exécution | Packagé |
|---|---|---|---|---|
| `compile` (par défaut) | oui | oui | oui | oui |
| `provided` | oui | oui | non (fourni par le conteneur) | non |
| `runtime` | non | oui | oui | oui |
| `test` | non | oui | non | non |

### Profils

```xml
<profiles>
  <profile>
    <id>prod</id>
    <properties>
      <spring.profiles.active>prod</spring.profiles.active>
    </properties>
  </profile>
  <profile>
    <id>jdk21</id>
    <activation><jdk>21</jdk></activation>
  </profile>
</profiles>
```

```bash
mvn package -Pprod
mvn package -P'!integration'                   # désactiver un profil
mvn help:active-profiles
mvn help:all-profiles
```

### Builds multi-modules

```bash
mvn -pl order-service package                  # uniquement ce module
mvn -pl order-service -am package              # + modules dont il dépend
mvn -pl order-service -amd package             # + modules qui dépendent de lui
mvn -rf :payment-service package               # reprendre après un échec
mvn -T 1C clean install                        # parallèle
```

### Versions et releases

```bash
mvn versions:display-dependency-updates
mvn versions:display-plugin-updates
mvn versions:set -DnewVersion=1.2.0 -DgenerateBackupPoms=false
mvn versions:use-latest-releases
mvn help:evaluate -Dexpression=project.version -q -DforceStdout   # afficher une valeur (utile en CI)
```

### Exécuter et déboguer

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
mvn spring-boot:run -Dspring-boot.run.jvmArguments="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"
mvn exec:java -Dexec.mainClass=com.acme.Main
mvn -Dmaven.surefire.debug test                # attend un débogueur sur le port 5005
```

### Maven Wrapper

```bash
mvn wrapper:wrapper -Dmaven=3.9.9              # génère mvnw + .mvn/wrapper
./mvnw clean verify                            # à utiliser en CI et dans le README
```

### Dépôt local et settings

```bash
mvn dependency:purge-local-repository          # retélécharge les dépendances du projet
rm -rf ~/.m2/repository/com/acme               # supprime un groupe (corrige les jars corrompus)
mvn -s ci-settings.xml package
mvn help:effective-settings
```

```xml
<!-- ~/.m2/settings.xml : identifiants et miroir -->
<settings>
  <servers>
    <server>
      <id>company-releases</id>
      <username>${env.NEXUS_USER}</username>
      <password>${env.NEXUS_PASS}</password>
    </server>
  </servers>
  <mirrors>
    <mirror>
      <id>company</id>
      <mirrorOf>*</mirrorOf>
      <url>https://nexus.example.com/repository/maven-public/</url>
    </mirror>
  </mirrors>
</settings>
```

---

## Gradle

### Wrapper

```bash
gradle wrapper --gradle-version 8.10           # génère gradlew + gradle/wrapper
./gradlew --version
./gradlew wrapper --gradle-version 8.10        # mise à jour
```

Commitez toujours le wrapper et utilisez `./gradlew`, pour que tout le monde construise avec le même Gradle.

### Tâches courantes

```bash
./gradlew tasks                                # tâches de ce projet
./gradlew tasks --all
./gradlew build                                # compile + test + assemble + check
./gradlew clean build
./gradlew assemble                             # package uniquement, sans tests
./gradlew check                                # tests + vérifications
./gradlew bootRun                              # Spring Boot
./gradlew bootJar
```

### Phase Maven vs tâche Gradle

| Maven | Gradle |
|---|---|
| `mvn compile` | `./gradlew compileJava` |
| `mvn test` | `./gradlew test` |
| `mvn package` | `./gradlew assemble` (ou `jar`) |
| `mvn verify` | `./gradlew check` |
| `mvn install` | `./gradlew publishToMavenLocal` |
| `mvn dependency:tree` | `./gradlew dependencies` |
| `mvn -pl mod -am` | `./gradlew :mod:build` (les dépendances sont construites automatiquement) |
| `mvn -DskipTests` | `./gradlew build -x test` |

### Options courantes

```bash
./gradlew build -x test                        # exclure une tâche
./gradlew build --info                         # plus de logs (--debug pour encore plus)
./gradlew build --stacktrace
./gradlew build --scan                         # publier un build scan
./gradlew build --offline
./gradlew build --refresh-dependencies         # comme mvn -U
./gradlew build --continue                     # continuer après les échecs
./gradlew build --parallel --build-cache
./gradlew --stop                               # arrêter les daemons (corrige les états bizarres)
./gradlew build --dry-run                      # liste les tâches qui s'exécuteraient
```

### Exécuter les tests

```bash
./gradlew test --tests OrderServiceTest
./gradlew test --tests 'OrderServiceTest.shouldRefund'
./gradlew test --tests '*Order*'
./gradlew :api:test --tests '*Foo'             # dans un seul module
./gradlew test --rerun-tasks                   # ignore les vérifications d'à-jour
./gradlew test -i                              # affiche la sortie standard des tests
./gradlew test --fail-fast
```

```text
> Task :test FAILED
OrderServiceTest > shouldRefund() FAILED
    org.opentest4j.AssertionFailedError at OrderServiceTest.java:42
```

Les rapports se trouvent dans `build/reports/tests/test/index.html`.

### Dépendances

```bash
./gradlew dependencies --configuration runtimeClasspath
./gradlew :api:dependencies --configuration compileClasspath
./gradlew dependencyInsight --dependency jackson-databind --configuration runtimeClasspath   # pourquoi cette version ?
./gradlew buildEnvironment                     # dépendances des plugins
```

### build.gradle.kts (Kotlin DSL)

```kotlin
plugins {
    java
    id("org.springframework.boot") version "3.3.2"
    id("io.spring.dependency-management") version "1.1.6"
}

group = "com.acme"
version = "1.0.0"

java {
    toolchain { languageVersion = JavaLanguageVersion.of(21) }   // provisionne automatiquement le JDK
}

repositories { mavenCentral() }

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    runtimeOnly("org.postgresql:postgresql")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

tasks.test {
    useJUnitPlatform()
    testLogging { events("failed", "skipped") }
}
```

### Configurations

| Gradle | Équivalent Maven |
|---|---|
| `implementation` | `compile` (non exposé aux consommateurs) |
| `api` (java-library) | `compile` (exposé) |
| `compileOnly` | `provided` |
| `runtimeOnly` | `runtime` |
| `testImplementation` | `test` |

### Forcer / exclure une version

```kotlin
configurations.all {
    resolutionStrategy {
        force("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    }
    exclude(group = "commons-logging", module = "commons-logging")
}
```

Contrairement à Maven, Gradle choisit par défaut la version **la plus élevée** demandée.

### Multi-projets

```kotlin
// settings.gradle.kts
rootProject.name = "shop"
include("order-service", "payment-service", "common")

// order-service/build.gradle.kts
dependencies { implementation(project(":common")) }
```

```bash
./gradlew projects
./gradlew :order-service:bootRun
./gradlew build -p order-service
```

### Tâche personnalisée et propriétés

```kotlin
tasks.register("hello") {
    group = "custom"
    doLast { println("Hello from ${project.name}") }
}
```

```bash
./gradlew hello
./gradlew build -Penv=prod                     # propriété de projet : findProperty("env")
./gradlew build -Dorg.gradle.jvmargs=-Xmx2g
```

```properties
# gradle.properties
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.jvmargs=-Xmx2g
```

### Déboguer le build

```bash
./gradlew test --debug-jvm                     # les tests attendent un débogueur sur 5005
./gradlew build --scan
./gradlew help --task test                     # options d'une tâche
./gradlew properties | grep -i version
```
