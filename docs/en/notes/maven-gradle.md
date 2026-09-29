# Maven and Gradle

## Maven

### Lifecycle

Running a phase runs every earlier phase of the same lifecycle.

| Phase | What happens |
|---|---|
| `validate` | Check the project is correct |
| `compile` | Compile `src/main` |
| `test` | Run unit tests (Surefire) |
| `package` | Build the jar/war in `target/` |
| `verify` | Run integration tests / checks (Failsafe) |
| `install` | Copy the artifact into `~/.m2` |
| `deploy` | Upload to a remote repository |

`clean` belongs to a separate lifecycle: it only deletes `target/`.

```bash
mvn clean package
mvn clean verify
mvn clean install -DskipTests
mvn compile                                    # fast feedback
```

### Common flags

| Flag | Effect |
|---|---|
| `-DskipTests` | Compile tests but do not run them |
| `-Dmaven.test.skip=true` | Do not even compile tests |
| `-o` | Offline mode |
| `-q` | Quiet |
| `-e` / `-X` | Show stack traces / full debug output |
| `-U` | Force update of snapshots and missing releases |
| `-T 1C` | One thread per CPU core (parallel build) |
| `-P prod` | Activate profile |
| `-pl mod -am` | Build module + what it depends on |
| `-rf :mod` | Resume the build from a module |
| `-fae` / `-ff` | Fail at end / fail fast |
| `-Dkey=value` | Set a property |

### Run tests
```bash
mvn test -Dtest=OrderServiceTest               # one class
mvn test -Dtest=OrderServiceTest#shouldRefund  # one method
mvn test -Dtest='Order*Test,!*IT'              # patterns
mvn verify -Dit.test=PaymentIT                 # Failsafe integration test
mvn test -Dsurefire.failIfNoSpecifiedTests=false -pl api -Dtest=Foo   # module without that test
mvn test -DargLine="-Xmx1g -Dspring.profiles.active=test"
mvn surefire-report:report                     # HTML report in target/site
```

### Dependency tree and analysis
```bash
mvn dependency:tree
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core
mvn dependency:tree -Dverbose                  # show omitted duplicates/conflicts
mvn dependency:analyze                         # unused declared / used undeclared
mvn dependency:resolve -Dclassifier=sources
mvn dependency:copy-dependencies -DoutputDirectory=target/lib
mvn help:effective-pom                         # POM after parents + profiles
```
```text
[INFO] com.acme:order-service:jar:1.0.0
[INFO] +- org.springframework.boot:spring-boot-starter-web:jar:3.3.2:compile
[INFO] |  +- com.fasterxml.jackson.core:jackson-databind:jar:2.17.2:compile
[INFO] |  |  \- com.fasterxml.jackson.core:jackson-core:jackson-core:2.17.2:compile
```

### Fix a version conflict
```xml
<!-- Pin a version for the whole project, including transitive uses -->
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

<!-- Or exclude one transitive dependency -->
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

Maven resolves conflicts by "nearest definition wins", then first declared. It does not pick the highest version.

### Dependency scopes

| Scope | Compile | Test | Runtime | Packaged |
|---|---|---|---|---|
| `compile` (default) | yes | yes | yes | yes |
| `provided` | yes | yes | no (container supplies it) | no |
| `runtime` | no | yes | yes | yes |
| `test` | no | yes | no | no |

### Profiles
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
mvn package -P'!integration'                   # deactivate a profile
mvn help:active-profiles
mvn help:all-profiles
```

### Multi-module builds
```bash
mvn -pl order-service package                  # only that module
mvn -pl order-service -am package              # + modules it depends on
mvn -pl order-service -amd package             # + modules that depend on it
mvn -rf :payment-service package               # resume after a failure
mvn -T 1C clean install                        # parallel
```

### Versions and releases
```bash
mvn versions:display-dependency-updates
mvn versions:display-plugin-updates
mvn versions:set -DnewVersion=1.2.0 -DgenerateBackupPoms=false
mvn versions:use-latest-releases
mvn help:evaluate -Dexpression=project.version -q -DforceStdout   # print a value (useful in CI)
```

### Run and debug
```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
mvn spring-boot:run -Dspring-boot.run.jvmArguments="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"
mvn exec:java -Dexec.mainClass=com.acme.Main
mvn -Dmaven.surefire.debug test                # waits for a debugger on port 5005
```

### Maven Wrapper
```bash
mvn wrapper:wrapper -Dmaven=3.9.9              # generate mvnw + .mvn/wrapper
./mvnw clean verify                            # use this in CI and README
```

### Local repo and settings
```bash
mvn dependency:purge-local-repository          # re-download project deps
rm -rf ~/.m2/repository/com/acme               # drop one group (fixes corrupt jars)
mvn -s ci-settings.xml package
mvn help:effective-settings
```
```xml
<!-- ~/.m2/settings.xml: credentials and mirror -->
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
gradle wrapper --gradle-version 8.10           # generate gradlew + gradle/wrapper
./gradlew --version
./gradlew wrapper --gradle-version 8.10        # upgrade
```

Always commit the wrapper and use `./gradlew`, so everyone builds with the same Gradle.

### Everyday tasks
```bash
./gradlew tasks                                # tasks of this project
./gradlew tasks --all
./gradlew build                                # compile + test + assemble + check
./gradlew clean build
./gradlew assemble                             # package only, no tests
./gradlew check                                # tests + verification
./gradlew bootRun                              # Spring Boot
./gradlew bootJar
```

### Maven phase vs Gradle task

| Maven | Gradle |
|---|---|
| `mvn compile` | `./gradlew compileJava` |
| `mvn test` | `./gradlew test` |
| `mvn package` | `./gradlew assemble` (or `jar`) |
| `mvn verify` | `./gradlew check` |
| `mvn install` | `./gradlew publishToMavenLocal` |
| `mvn dependency:tree` | `./gradlew dependencies` |
| `mvn -pl mod -am` | `./gradlew :mod:build` (deps are built automatically) |
| `mvn -DskipTests` | `./gradlew build -x test` |

### Common flags
```bash
./gradlew build -x test                        # exclude a task
./gradlew build --info                         # more logging (--debug for even more)
./gradlew build --stacktrace
./gradlew build --scan                         # publish a build scan
./gradlew build --offline
./gradlew build --refresh-dependencies         # like mvn -U
./gradlew build --continue                     # keep going after failures
./gradlew build --parallel --build-cache
./gradlew --stop                               # stop daemons (fixes odd state)
./gradlew build --dry-run                      # list tasks that would run
```

### Run tests
```bash
./gradlew test --tests OrderServiceTest
./gradlew test --tests 'OrderServiceTest.shouldRefund'
./gradlew test --tests '*Order*'
./gradlew :api:test --tests '*Foo'             # in one module
./gradlew test --rerun-tasks                   # ignore up-to-date checks
./gradlew test -i                              # show test stdout
./gradlew test --fail-fast
```
```text
> Task :test FAILED
OrderServiceTest > shouldRefund() FAILED
    org.opentest4j.AssertionFailedError at OrderServiceTest.java:42
```
Reports are in `build/reports/tests/test/index.html`.

### Dependencies
```bash
./gradlew dependencies --configuration runtimeClasspath
./gradlew :api:dependencies --configuration compileClasspath
./gradlew dependencyInsight --dependency jackson-databind --configuration runtimeClasspath   # why this version?
./gradlew buildEnvironment                     # plugin dependencies
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
    toolchain { languageVersion = JavaLanguageVersion.of(21) }   // auto-provisions the JDK
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

| Gradle | Maven equivalent |
|---|---|
| `implementation` | `compile` (not exposed to consumers) |
| `api` (java-library) | `compile` (exposed) |
| `compileOnly` | `provided` |
| `runtimeOnly` | `runtime` |
| `testImplementation` | `test` |

### Force / exclude a version
```kotlin
configurations.all {
    resolutionStrategy {
        force("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    }
    exclude(group = "commons-logging", module = "commons-logging")
}
```
Unlike Maven, Gradle picks the **highest** requested version by default.

### Multi-project
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

### Custom task and properties
```kotlin
tasks.register("hello") {
    group = "custom"
    doLast { println("Hello from ${project.name}") }
}
```
```bash
./gradlew hello
./gradlew build -Penv=prod                     # project property: findProperty("env")
./gradlew build -Dorg.gradle.jvmargs=-Xmx2g
```
```properties
# gradle.properties
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.jvmargs=-Xmx2g
```

### Debug the build
```bash
./gradlew test --debug-jvm                     # tests wait for a debugger on 5005
./gradlew build --scan
./gradlew help --task test                     # options of a task
./gradlew properties | grep -i version
```
