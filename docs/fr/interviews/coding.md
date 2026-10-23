# Live coding & algorithmes

Les entretiens full-stack seniors demandent rarement des algorithmes exotiques. Ils vérifient que vous savez transformer un problème en code propre et testé tout en parlant, choisir la bonne structure de données et raisonner sur la complexité. Le fonctionnement interne des collections Java est traité dans [Java Q6](java-core-jvm.md#arraylist-linkedlist-hashmap-treemap-linkedhashmap) et [Java Q18](java-core-jvm.md#happens-inside-hashmap-put-get).

## 🟢 Fondamentaux

### Méthode

#### Q1. Comment aborder un exercice de live coding ? {#approach-live-coding-exercise}
**Réponse :** Suivez un processus visible, car l'intervieweur l'évalue autant que le résultat.

1. **Clarifier** (2–3 min) : reformulez le problème, demandez la taille de l'entrée, les entrées vides ou nulles, les
   doublons, les nombres négatifs, si c'est trié, et la sortie attendue pour un exemple.
2. **Exemples** : écrivez deux ou trois petits cas, dont un cas limite.
3. **Force brute d'abord** : énoncez-la à voix haute avec sa complexité, puis améliorez si besoin.
4. **Planifiez** la meilleure approche en une ou deux phrases avant de taper.
5. **Codez** avec des noms clairs et de petites méthodes utilitaires ; parlez en tapant.
6. **Testez** en déroulant vos exemples à la main, puis les cas limites ; corrigez les bugs calmement.
7. **Analysez** la complexité en temps et en espace, et dites ce que vous feriez avec plus de temps.

**Exemple :**

```text
"Donc l'entrée est un tableau non trié d'au plus 10^5 entiers, éventuellement négatifs, et je renvoie
les indices de deux nombres dont la somme vaut target, avec exactement une réponse garantie ? La force
brute teste O(n²) paires ; avec une HashMap valeur → indice je le fais en une passe, O(n) en temps et
O(n) en espace. Je code ça."
```

#### Q2. Comment expliquer le Big-O, et quelles complexités faut-il connaître par cœur ? {#big-o-complexities-know-heart}
**Réponse :** Le Big-O décrit comment le temps ou la mémoire **croît avec la taille de l'entrée** dans le pire cas, en
ignorant les constantes. À connaître : O(1) recherche dans une table de hachage et accès par indice ; O(log n)
recherche dichotomique et opérations d'arbre équilibré (`TreeMap`) ; O(n) une passe ; O(n log n) tri par comparaison
(`List.sort`, `Arrays.sort` sur des objets) ; O(n²) boucles imbriquées sur la même entrée ; O(2ⁿ) tous les
sous-ensembles. Traduisez en taille d'entrée : pour n = 10⁵, O(n²) fait 10¹⁰ opérations, trop lent ; O(n log n) environ
1,7 million, instantané. Donnez aussi la complexité en **espace** et les coûts amortis (`ArrayList.add` est en O(1)
amorti).

**Exemple :**

```text
n = 1 000 000
O(n)        1e6 ops    ✅ ~ms
O(n log n)  2e7 ops    ✅
O(n²)       1e12 ops   ⛔ des heures
```

#### Q3. Quelles structures de données Java utiliser dans les exercices de code ? {#java-data-structures-coding-exercises}
**Réponse :** `HashMap`/`HashSet` pour la recherche en O(1), le comptage et la déduplication ; `ArrayList` pour les
listes indexées ; `ArrayDeque` comme pile (`push`/`pop`) et comme file (`offer`/`poll`) ; `PriorityQueue` comme tas
min (passez `Comparator.reverseOrder()` pour un tas max) ; `TreeMap`/`TreeSet` pour l'ordre trié et les requêtes
floor/ceiling ; `int[]`/`boolean[]` pour les compteurs de taille fixe et les drapeaux de visite (plus rapides que les
collections de types boxés) ; `StringBuilder` pour construire des chaînes en boucle. Connaissez les méthodes pratiques :
`getOrDefault`, `merge`, `computeIfAbsent`, `Arrays.fill`, `Collections.swap`.

**Exemple :**

```java
Map<Character, Integer> freq = new HashMap<>();
for (char c : s.toCharArray()) freq.merge(c, 1, Integer::sum);

Map<String, List<String>> groups = new HashMap<>();
groups.computeIfAbsent(key, k -> new ArrayList<>()).add(word);
```

### Patterns essentiels

#### Q4. Quand utiliser une table de hachage pour passer de O(n²) à O(n) ? Résolvez « two sum ». {#hash-map-turn-o-n2}
**Réponse :** Dès que la force brute consiste à « pour chaque élément, chercher un partenaire dans le reste », stockez
ce que vous avez déjà vu dans une table de hachage indexée par ce que vous devrez rechercher. Pour two sum, pour chaque
nombre vérifiez si `target - x` a été vu, puis enregistrez `x`. Une passe, O(n) en temps, O(n) en espace.

**Exemple :**

```java
int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();          // valeur -> indice
    for (int i = 0; i < nums.length; i++) {
        Integer j = seen.get(target - nums[i]);
        if (j != null) return new int[] { j, i };
        seen.put(nums[i], i);
    }
    throw new IllegalArgumentException("no solution");
}
```

#### Q5. Trouver les éléments en double dans une liste. {#find-duplicate-elements-list}
**Réponse :** Clarifiez d'abord : renvoyer chaque valeur qui apparaît plus d'une fois (une seule fois chacune), ou seulement
le premier doublon ? Conserver l'ordre d'entrée ? La solution standard est un **`HashSet`** : parcourir une fois, `add` renvoie
`false` quand la valeur a déjà été vue. C'est O(n) en temps et O(n) en espace, contre O(n²) pour comparer toutes les paires.
Utilisez un second ensemble (ou un `LinkedHashSet`) pour les doublons afin que chacun soit signalé une fois et dans l'ordre de
première apparition. Si la mémoire supplémentaire est interdite et que la liste peut être triée, trier d'abord (O(n log n))
rend les doublons adjacents. Si les valeurs sont dans `1..n`, on peut marquer les indices visités en place. Avec les streams,
`Collectors.groupingBy(identity(), counting())` est lisible mais construit une table de comptage complète. Cas limites :
liste vide, éléments `null` (`HashSet` accepte un null ; `List.of` le refuse), et correction de `equals`/`hashCode` pour les
types personnalisés.

**Exemple :**

```java
static <T> Set<T> duplicates(Collection<T> items) {
    Set<T> seen = new HashSet<>();
    Set<T> dups = new LinkedHashSet<>();                 // conserve l'ordre du premier doublon
    for (T item : items) {
        if (!seen.add(item)) dups.add(item);            // add() == false -> déjà vu
    }
    return dups;
}
// duplicates(List.of(3, 1, 3, 2, 1, 3))  ->  [3, 1]      O(n) en temps, O(n) en espace
```

**Pourquoi c'est un piège :** la version à boucles imbriquées marche sur l'exemple et échoue sur un million de lignes, et un
`List.contains` dans la boucle est le même O(n²) déguisé. Des clés mutables avec un mauvais `hashCode` cassent silencieusement
l'ensemble (voir [Java Q19](java-core-jvm.md#mutable-object-field-based-hashcode)).

#### Q6. Trouver le premier caractère non répété d'une chaîne. {#find-first-non-repeating-character}
**Réponse :** Deux passes avec une table de fréquences : la passe 1 compte chaque caractère, la passe 2 renvoie le premier
caractère dont le compte vaut 1. Temps O(n), espace O(k) où k est la taille de l'alphabet (O(1) pour de l'ASCII avec un
`int[256]`, plus grand pour Unicode). Une seule passe est possible avec une `LinkedHashMap` qui garde l'ordre d'insertion, puis
on parcourt la table pour trouver le premier compte égal à 1, mais la version en deux passes est plus simple et aussi rapide.
Clarifiez le contrat avant de coder : sensibilité à la casse, que renvoyer s'il n'y en a pas (`Optional<Character>`, indice
`-1` ou `null`), et Unicode : un `char` est une unité de code UTF-16, donc les emojis et certaines lettres accentuées sont des
paires de substitution ; itérez sur `codePoints()` si cela compte. Tests : chaîne vide, tout répété (`"aabb"`), un seul
caractère, le caractère unique tout à la fin.

**Exemple :**

```java
static OptionalInt firstUniqueIndex(String s) {
    Map<Integer, Integer> count = new HashMap<>();
    s.codePoints().forEach(cp -> count.merge(cp, 1, Integer::sum));       // passe 1 : fréquences

    int i = 0;
    for (int cp : s.codePoints().toArray()) {                              // passe 2 : premier avec compte == 1
        if (count.get(cp) == 1) return OptionalInt.of(i);
        i += Character.charCount(cp);                                      // indice en chars, pas en points de code
    }
    return OptionalInt.empty();
}
// "swiss" -> indice 1 ('w');  "aabb" -> vide;  "" -> vide
```

**Pourquoi c'est un piège :** utiliser `s.indexOf(c) == s.lastIndexOf(c)` pour chaque caractère est en O(n²), et un `int[26]`
échoue dès que l'entrée contient majuscules, chiffres ou accents. De plus, renvoyer un `' '` ou `0` magique pour « non trouvé »
est ambigu quand la chaîne peut le contenir.

#### Q7. Que sont les patterns two pointers et sliding window ? Résolvez « plus longue sous-chaîne sans caractère répété ». {#two-pointer-sliding-window-patterns}
**Réponse :** Les **two pointers** avancent depuis les deux extrémités (tableaux triés, palindromes) ou à des vitesses
différentes (détection de cycle). Une **fenêtre glissante** maintient un intervalle `[left, right]` qui respecte une
condition : on étend `right`, et quand la condition casse, on avance `left` jusqu'à ce qu'elle soit de nouveau vraie.
Chaque indice entre et sort une seule fois, donc c'est O(n). Pour la plus longue sous-chaîne sans répétition, gardez
le dernier indice de chaque caractère et faites sauter `left` après une répétition.

**Exemple :**

```java
int lengthOfLongestSubstring(String s) {
    Map<Character, Integer> last = new HashMap<>();
    int best = 0;
    for (int left = 0, right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        if (last.containsKey(c) && last.get(c) >= left) left = last.get(c) + 1;
        last.put(c, right);
        best = Math.max(best, right - left + 1);
    }
    return best;   // "abcabcbb" -> 3
}
```

#### Q8. Comment écrire une recherche dichotomique sans erreur d'un indice ? {#write-binary-search-off-one}
**Réponse :** Utilisez un seul modèle cohérent : un intervalle semi-ouvert ou fermé, une condition de boucle qui lui
correspond, et `mid = lo + (hi - lo) / 2` pour éviter le dépassement. La forme la plus réutilisable cherche le **premier
indice où une condition devient vraie** (lower bound), ce qui couvre aussi « position d'insertion », « première
version défectueuse » et la dichotomie sur la réponse (capacité minimale, vitesse minimale).

**Exemple :**

```java
// premier indice i dans [0, n] tel que a[i] >= target (n si aucun)
int lowerBound(int[] a, int target) {
    int lo = 0, hi = a.length;               // semi-ouvert [lo, hi)
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] >= target) hi = mid; else lo = mid + 1;
    }
    return lo;
}
```

#### Q9. BFS ou DFS — quand utiliser chacun ? Résolvez « nombre d'îles ». {#bfs-dfs-each-solve-number}
**Réponse :** Le **BFS** (file) explore niveau par niveau, donc il trouve le **plus court chemin dans un graphe non
pondéré** (nombre minimal de coups, degrés de séparation). Le **DFS** (récursion ou pile explicite) va d'abord en
profondeur, adapté à l'exploration des composantes connexes, la détection de cycles, le tri topologique et le
backtracking. Les deux sont en O(V + E). Dans une grille, chaque case est un nœud avec jusqu'à quatre voisins ; marquez
les cases visitées pour éviter les boucles infinies. Pour des entrées profondes, préférez en Java une pile explicite ou
le BFS pour éviter un `StackOverflowError`.

**Exemple :**

```java
int numIslands(char[][] grid) {
    int count = 0;
    int[][] dirs = { {1,0}, {-1,0}, {0,1}, {0,-1} };
    for (int r = 0; r < grid.length; r++)
        for (int c = 0; c < grid[0].length; c++) {
            if (grid[r][c] != '1') continue;
            count++;
            Deque<int[]> queue = new ArrayDeque<>(List.of(new int[] { r, c }));
            grid[r][c] = '0';
            while (!queue.isEmpty()) {
                int[] cell = queue.poll();
                for (int[] d : dirs) {
                    int nr = cell[0] + d[0], nc = cell[1] + d[1];
                    if (nr >= 0 && nr < grid.length && nc >= 0 && nc < grid[0].length && grid[nr][nc] == '1') {
                        grid[nr][nc] = '0';
                        queue.offer(new int[] { nr, nc });
                    }
                }
            }
        }
    return count;
}
```

#### Q10. Quand un tas est-il le bon outil ? Résolvez « top K éléments les plus fréquents ». {#heap-right-tool-solve-top}
**Réponse :** Utilisez un tas quand vous avez besoin à répétition du plus petit ou du plus grand élément d'un ensemble
qui change : top K, fusion de K listes, ordonnancement, Dijkstra. Pour le top K parmi n, gardez un **tas min de taille
K** : insérez chaque candidat et retirez le minimum quand la taille dépasse K. C'est O(n log K) en temps et O(K) pour
le tas, mieux que trier tout (O(n log n)) quand K est petit.

**Exemple :**

```java
List<Integer> topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int n : nums) freq.merge(n, 1, Integer::sum);

    PriorityQueue<Map.Entry<Integer, Integer>> heap =
        new PriorityQueue<>(Map.Entry.comparingByValue());          // tas min par fréquence
    for (var e : freq.entrySet()) {
        heap.offer(e);
        if (heap.size() > k) heap.poll();
    }
    return heap.stream().map(Map.Entry::getKey).toList();
}
```

## 🟡 Pièges seniors

### Questions

#### Q11. Quels pièges Java font perdre des points en live coding ? {#java-pitfalls-cost-candidates-points}
**Réponse :** Le **dépassement d'entier** (`(lo + hi) / 2`, sommes de grands entiers : utilisez `long`) ; comparer
des nombres boxés avec `==` (`Integer` au-delà de 127, voir [Java Q9](java-core-jvm.md#autoboxing-trap-integer)) ; un comparateur écrit
`a - b`, qui déborde (utilisez `Integer.compare`) ; la concaténation de chaînes en boucle (O(n²) ; utilisez
`StringBuilder`) ; modifier une collection pendant un parcours for-each ; `Arrays.asList` qui renvoie une liste de
taille fixe ; la profondeur de récursion sur de grandes entrées ; oublier l'entrée vide ; et l'arithmétique sur `char`
(`c - 'a'` est correct, `c + 1` est un `int`).

**Exemple :**

```java
// ⛔ déborde pour de grandes valeurs de signes opposés
list.sort((a, b) -> a - b);
// ✅
list.sort(Integer::compare);
```

**Pourquoi c'est un piège :** l'algorithme est juste et le cas de test passe ; l'intervieweur demande alors « et si les
valeurs sont proches de `Integer.MAX_VALUE` ? », et le bug est dans la ligne à laquelle vous n'avez pas pensé.

#### Q12. Regrouper des rendez-vous par médecin et par date avec les streams. {#group-appointments-doctor-date-streams}
**Réponse :** `Collectors.groupingBy` avec un collecteur *aval* le fait en une passe. Pour un regroupement à deux niveaux,
imbriquez les collecteurs : médecin → date → liste. Choisissez le type de map délibérément : `TreeMap` pour des clés triées
(dates dans l'ordre), `LinkedHashMap` pour garder l'ordre de rencontre, et triez les listes internes
(`Comparator.comparing(Appointment::start)`) car `groupingBy` ne conserve l'ordre d'entrée qu'au sein de chaque groupe.
Utilisez `mapping` pour ne collecter que des identifiants, `counting()` pour des totaux et `summingInt` pour des durées ;
`toUnmodifiableList` pour des résultats en lecture seule. Modélisez la clé explicitement (un petit
`record DoctorDay(String doctorId, LocalDate day)`) si vous voulez une seule map plate. Temps O(n log n) avec tri, O(n) sans ;
mémoire proportionnelle aux données. Piège du fuseau horaire : dérivez la date de l'instant *dans le fuseau du praticien*, pas
celui par défaut du serveur, sinon les rendez-vous de fin de soirée tombent le mauvais jour. Cas limites : entrée vide (map
vide, pas `null`), champs `null`, rendez-vous annulés (filtrer d'abord). Un stream parallèle exige ici `groupingByConcurrent`,
et en vaut rarement la peine.

**Exemple :**

```java
record Appointment(String id, String doctorId, Instant start, Duration length, boolean cancelled) {}

Map<String, Map<LocalDate, List<Appointment>>> byDoctorAndDay = appointments.stream()
    .filter(a -> !a.cancelled())
    .collect(Collectors.groupingBy(
        Appointment::doctorId,
        TreeMap::new,                                                    // médecins triés
        Collectors.groupingBy(
            a -> a.start().atZone(ZoneId.of("Europe/Paris")).toLocalDate(),
            TreeMap::new,                                                // jours triés
            Collectors.collectingAndThen(Collectors.toList(), list -> {
                list.sort(Comparator.comparing(Appointment::start));     // ordre dans la journée
                return List.copyOf(list);
            }))));

// Variante : minutes réservées par médecin
Map<String, Long> minutes = appointments.stream().filter(a -> !a.cancelled())
    .collect(groupingBy(Appointment::doctorId, summingLong(a -> a.length().toMinutes())));
```

**Pourquoi c'est un piège :** oublier le fuseau horaire, supposer que `groupingBy` renvoie des clés triées (il renvoie une
`HashMap`), et modifier une liste depuis le stream. Voir aussi les pièges des streams dans
[Java Q14](java-core-jvm.md#common-ways-stream-pipeline-goes).

#### Q13. Détecter des réservations qui se chevauchent. {#detect-overlapping-bookings}
**Réponse :** Deux plages horaires se chevauchent exactement quand `a.start < b.end && b.start < a.end`. Traitez les plages
comme **semi-ouvertes** `[début, fin)` pour que des rendez-vous consécutifs (10:00–10:30 et 10:30–11:00) n'entrent *pas* en
conflit ; cette seule décision cause la plupart des bugs d'écart d'un, dites-la à voix haute. Pour une nouvelle réservation
face à une liste existante, testez la condition contre chaque réservation, O(n), ou O(log n) si les réservations sont gardées
dans une `TreeMap<Instant, Booking>` indexée par début : regardez `floorEntry(start)` (la précédente doit finir avant `start`)
et `ceilingEntry(start)` (la suivante doit commencer à `end` ou après). Pour trouver *tous* les conflits d'un lot, **triez par
début et balayez** : gardez la fin la plus tardive vue jusque-là et signalez un conflit chaque fois que le début suivant lui
est antérieur. Temps O(n log n), espace supplémentaire O(1). Utilisez `Instant` ou `ZonedDateTime`, jamais `LocalDateTime` à
travers fuseaux horaires ou changements d'heure, et validez `start < end`. En production, le contrôle doit être imposé par la
base (contrainte d'exclusion, voir [Persistence Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)), car une vérification en mémoire
est en concurrence avec les autres requêtes.

**Exemple :**

```java
record Booking(String id, Instant start, Instant end) {
    boolean overlaps(Booking o) { return start.isBefore(o.end) && o.start.isBefore(end); }
}

static List<Booking[]> conflicts(List<Booking> bookings) {
    List<Booking> sorted = bookings.stream().sorted(Comparator.comparing(Booking::start)).toList();
    List<Booking[]> result = new ArrayList<>();
    Booking latest = null;                                   // réservation dont la fin est la plus tardive
    for (Booking b : sorted) {
        if (latest != null && b.start().isBefore(latest.end())) result.add(new Booking[]{latest, b});
        if (latest == null || b.end().isAfter(latest.end())) latest = b;
    }
    return result;                                           // chaque réservation est comparée à celle qui va le plus loin
}
// A 10:00-11:00, B 10:30-10:45, C 10:50-11:30 : signale (A,B) et (A,C) ; B dans A n'est pas manqué.
```

**Pourquoi c'est un piège :** utiliser `<=` au lieu de `<` signale les créneaux consécutifs, un cas d'inclusion (une
réservation à l'intérieur d'une longue) est manqué si l'on ne compare que les voisines, et comparer des `LocalDateTime`
ignore les fuseaux horaires. Testez les trois formes : chevauchement partiel, inclusion et extrémités qui se touchent.

#### Q14. Qu'est-ce que la programmation dynamique, et comment repérer un problème de DP ? {#dynamic-programming-spot-dp-problem}
**Réponse :** La DP s'applique quand un problème a des **sous-problèmes qui se recouvrent** et une **sous-structure
optimale** : la meilleure réponse se construit à partir des meilleures réponses à des versions plus petites, et ces
mêmes versions reviennent sans cesse. Signaux : « nombre de façons », « coût minimal », « plus longue/courte ...
sous-séquence », des choix à chaque étape. Méthode : définissez l'**état** (ce que signifie `dp[i]`), la
**transition** (comment `dp[i]` découle d'états plus petits) et les **cas de base**. Commencez par une récursion avec
mémoïsation (top-down), puis passez à un tableau (bottom-up) et réduisez souvent l'espace à quelques variables.

**Exemple :**

```java
// Nombre minimal de pièces pour un montant ; dp[a] = minimum de pièces pour le montant a
int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, Integer.MAX_VALUE);
    dp[0] = 0;
    for (int a = 1; a <= amount; a++)
        for (int c : coins)
            if (c <= a && dp[a - c] != Integer.MAX_VALUE)
                dp[a] = Math.min(dp[a], dp[a - c] + 1);
    return dp[amount] == Integer.MAX_VALUE ? -1 : dp[amount];
}
```

**Pourquoi c'est un piège :** un algorithme glouton « prendre d'abord la plus grosse pièce » passe sur `{1, 5, 10}` et
échoue sur `{1, 3, 4}` pour un montant de 6 (le glouton donne 3 pièces, l'optimum est 2). Testez toujours une idée
gloutonne contre un contre-exemple.

#### Q15. Implémenter un compteur thread-safe. {#implement-thread-safe-counter}
**Réponse :** `count++` fait trois étapes (lire, ajouter, écrire), donc deux threads peuvent lire 5 et écrire tous deux 6 : une
mise à jour perdue. Options, de la plus simple à la plus scalable : (1) des méthodes **`synchronized`** ou un `ReentrantLock` :
correct, mais les threads font la queue à chaque appel ; (2) **`AtomicLong`/`AtomicInteger`** : `incrementAndGet()` utilise un
compare-and-swap matériel, sans verrou, et c'est le bon choix par défaut pour un compteur dont on lit aussi la valeur ; sous
très forte contention la boucle CAS réessaie beaucoup ; (3) **`LongAdder`** : répartit les mises à jour sur des cellules
internes et les additionne dans `sum()`, bien plus rapide sous forte contention en écriture (métriques, compteurs de
requêtes), mais `sum()` n'est pas un instantané atomique et il n'offre pas de compare-and-set, donc il est inadapté pour
« incrémenter *seulement si* sous une limite ». (4) Ne pas partager du tout : des compteurs par thread fusionnés à la fin. Un
`volatile long` seul **ne suffit pas** : il garantit la visibilité mais pas l'atomicité de `++` (voir
[Java Q23](java-core-jvm.md#real-synchronized-volatile)). Pour un compteur borné (limite de débit, « maximum 3 réservations »), utilisez une boucle CAS
avec `updateAndGet`/`compareAndSet` pour que le test et l'incrément forment une seule étape atomique. Testez avec beaucoup de
threads et vérifiez le total exact ; un test mono-thread ne prouve rien.

**Exemple :**

```java
class Counter {
    private final AtomicLong value = new AtomicLong();
    long increment() { return value.incrementAndGet(); }
    long get()       { return value.get(); }
}

class BoundedCounter {                                    // test et incrément doivent former une seule étape atomique
    private final AtomicInteger value = new AtomicInteger();
    boolean tryIncrement(int max) {
        int cur;
        do { cur = value.get(); if (cur >= max) return false; }
        while (!value.compareAndSet(cur, cur + 1));
        return true;
    }
}

// Test : 100 threads x 10_000 incréments doivent donner exactement 1_000_000
ExecutorService pool = Executors.newFixedThreadPool(100);
Counter c = new Counter();
List<Future<?>> fs = IntStream.range(0, 100).mapToObj(i -> pool.submit(() -> { for (int j = 0; j < 10_000; j++) c.increment(); })).toList();
for (Future<?> f : fs) f.get();
assertEquals(1_000_000, c.get());
```

**Pourquoi c'est un piège :** `volatile` et `ConcurrentHashMap<String, Integer>` avec `map.put(k, map.get(k) + 1)` semblent
thread-safe et ne le sont pas ; utilisez `merge(k, 1, Integer::sum)` ou une valeur `LongAdder`. De plus, un compteur atomique
protège un nombre, pas un invariant portant sur deux champs.

#### Q16. Implémenter une logique de nouvelle tentative (retry) avec un nombre maximal de tentatives. {#implement-retry-logic-maximum-number}
**Réponse :** Un utilitaire de retry reçoit une opération, un nombre maximal de tentatives, une politique de délai et un
prédicat indiquant quels échecs sont rejouables. Décisions à énoncer : (1) **ne rejouer que les erreurs transitoires**
(timeouts, `503`, connexion coupée, victime de deadlock), jamais les erreurs de validation ou `4xx`, et **seulement les
opérations idempotentes**, ou protégées par une clé d'idempotence, sinon un retry après une réponse perdue duplique un
paiement ou une réservation (voir [Full Stack Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need)) ; (2) **le borner** : un nombre maximal de
tentatives (par ex. 3) et une échéance globale ; (3) **attente exponentielle avec jitter** (100 ms, 200 ms, 400 ms,
randomisés) pour que de nombreux clients ne rejouent pas en phase et n'écrasent pas un service en récupération (*tempête de
retries*) ; (4) **relancer le dernier échec en y attachant les précédents** (`addSuppressed`) pour ne rien perdre ; (5)
**rétablir le drapeau d'interruption** si l'attente est interrompue et s'arrêter ; (6) les retries se multiplient entre les
couches (3 retries sur 3 couches = 27 appels), donc rejouez à une seule couche et combinez avec un circuit breaker. Avec
Spring, `@Retryable`/Spring Retry (ou le `Retry` de Resilience4j) le font de façon déclarative, mais l'écrire à la main est la
question de live coding. Testez avec un faux qui échoue N fois : vérifiez exactement `max` tentatives, aucun retry sur une
exception non rejouable, et des délais croissants (injectez le « sleeper » pour que les tests n'attendent pas vraiment).

**Exemple :**

```java
static <T> T retry(int maxAttempts, Duration baseDelay, Predicate<Exception> retryable,
                   Callable<T> op, LongConsumer sleeper) throws Exception {
    if (maxAttempts < 1) throw new IllegalArgumentException("maxAttempts must be >= 1");
    Exception last = null;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return op.call();
        } catch (Exception e) {
            if (!retryable.test(e)) throw e;                           // échec permanent : ne pas rejouer
            if (last != null) e.addSuppressed(last);
            last = e;
            if (attempt == maxAttempts) break;
            long exp = baseDelay.toMillis() << (attempt - 1);          // 100, 200, 400 ...
            long jitter = ThreadLocalRandom.current().nextLong(exp / 2 + 1);
            try { sleeper.accept(exp / 2 + jitter); }                  // « equal jitter »
            catch (RuntimeException ie) { Thread.currentThread().interrupt(); throw e; }
        }
    }
    throw last;
}
// usage : retry(3, Duration.ofMillis(100), e -> e instanceof IOException, () -> client.call(), enveloppe-de-Thread::sleep)
```

**Pourquoi c'est un piège :** rejouer des appels non idempotents, rejouer indéfiniment, pas de jitter, et avaler l'exception
d'origine sont les quatre erreurs classiques. Rappelez-vous aussi qu'un retry n'est pas gratuit : avec une dépendance lente il
garde threads et connexions occupés plus longtemps, donc associez-le à des timeouts et à un circuit breaker (voir
[Spring Q35](spring-architecture.md#circuit-breaker-pattern-service-need)).

#### Q17. Implémentez un cache LRU avec `get` et `put` en O(1). {#implement-lru-cache-o-1}
**Réponse :** Il faut une recherche en O(1) (une table de hachage) et des opérations « passer en plus récent » et
« évincer le plus ancien » en O(1) (une liste doublement chaînée). En Java, `LinkedHashMap` avec `accessOrder = true`
et une redéfinition de `removeEldestEntry` fournit exactement cela en quelques lignes. Les intervieweurs demandent
souvent ensuite de le construire à la main (map de clé vers nœud, plus une liste doublement chaînée avec des
sentinelles en tête et en queue) : soyez prêt pour les deux. La sûreté multi-thread et les compromis de mémoire bornée
sont traités dans [Java Q21](java-core-jvm.md#design-thread-safe-bounded-lru).

**Exemple :**

```java
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;
    LruCache(int capacity) { super(16, 0.75f, true); this.capacity = capacity; }   // ordre d'accès
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) { return size() > capacity; }
}
```

**Pourquoi c'est un piège :** une `LinkedList` simple avec `remove(Object)` pour déplacer une clé semble correcte mais
coûte O(n) par accès.

#### Q18. Comment tester votre code pendant l'entretien ? {#test-code-during-interview}
**Réponse :** Ne vous contentez pas de « ça a l'air bon ». Déroulez un exemple normal ligne par ligne en suivant les
variables à voix haute. Puis passez les cas limites : entrée vide, un seul élément, tous les éléments égaux, réponse en
première ou dernière position, nombres négatifs, et la plus grande entrée pour la performance. Si l'environnement
permet d'exécuter le code, écrivez un petit `main` ou quelques assertions façon JUnit. Quand vous trouvez un bug,
expliquez la cause avant de corriger : c'est ce réflexe de débogage que l'intervieweur cherche.

**Exemple :**

```java
assert lengthOfLongestSubstring("") == 0;
assert lengthOfLongestSubstring("bbbb") == 1;
assert lengthOfLongestSubstring("abba") == 2;      // détecte le bug « left recule »
```

**Pourquoi c'est un piège :** la plupart des exercices ratés ne viennent pas d'un mauvais algorithme mais de cas limites
non testés que le candidat aurait trouvés en une minute.

## 🔴 Expert / Ouvert

### Questions

#### Q19. Concevez et codez une classe de rate limiter pour une seule instance de service. {#design-code-rate-limiter-class}
**Réponse :** Clarifiez d'abord : par utilisateur ou global, limite et fenêtre, comportement en cas de rejet, besoin
de sûreté multi-thread. Un **token bucket** est la réponse habituelle : chaque clé a un seau de capacité C rempli à R
jetons par seconde ; une requête prend un jeton ou est rejetée. Stockez l'état par clé dans une `ConcurrentHashMap` et
mettez-le à jour de façon atomique (`compute`, ou synchronisation sur le seau). Utilisez une `Clock` ou un fournisseur
de nanoTime pour que les tests contrôlent le temps. Discutez ensuite des limites : la mémoire pour de nombreuses clés
(évincer les seaux inactifs), et la limitation distribuée, qui nécessite Redis (voir
[System Design Q15](system-design.md#compare-rate-limiting-algorithms-one)).

**Exemple :**

```java
class TokenBucketLimiter {
    private record Bucket(double tokens, long lastNanos) {}
    private final ConcurrentHashMap<String, Bucket> buckets = new ConcurrentHashMap<>();
    private final double capacity, refillPerNano;
    private final LongSupplier nanoTime;

    TokenBucketLimiter(double capacity, double refillPerSecond, LongSupplier nanoTime) {
        this.capacity = capacity; this.refillPerNano = refillPerSecond / 1e9; this.nanoTime = nanoTime;
    }

    boolean tryAcquire(String key) {
        boolean[] allowed = new boolean[1];
        buckets.compute(key, (k, b) -> {
            long now = nanoTime.getAsLong();
            double tokens = b == null ? capacity : Math.min(capacity, b.tokens() + (now - b.lastNanos()) * refillPerNano);
            allowed[0] = tokens >= 1;
            return new Bucket(allowed[0] ? tokens - 1 : tokens, now);
        });
        return allowed[0];
    }
}
```

#### Q20. Fusionnez des intervalles qui se chevauchent ; comment la solution change-t-elle pour un flux d'intervalles ? {#merge-overlapping-intervals-solution-change}
**Réponse :** Pour une liste, **triez par début** (O(n log n)), puis parcourez : si l'intervalle suivant commence avant
ou à la fin courante, prolongez la fin ; sinon fermez l'intervalle courant et en commencez un nouveau. Pour un **flux**
(intervalles arrivant un par un, comme des réservations d'agenda), gardez les intervalles fusionnés dans une
`TreeMap<début, fin>` et, à chaque insertion, regardez `floorEntry` et les entrées suivantes pour fusionner en
O(log n + fusionnés). C'est un bon exemple de la relance qu'aiment les intervieweurs : « maintenant les données ne
tiennent plus dans un seul appel ».

**Exemple :**

```java
int[][] merge(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(i -> i[0]));
    List<int[]> out = new ArrayList<>();
    for (int[] cur : intervals) {
        if (!out.isEmpty() && cur[0] <= out.getLast()[1])
            out.getLast()[1] = Math.max(out.getLast()[1], cur[1]);
        else out.add(cur);
    }
    return out.toArray(int[][]::new);
}
```

#### Q21. Étant donné les horaires de travail d'un praticien et ses rendez-vous existants, trouver les créneaux disponibles. {#given-practitioner-working-hours-existing}
**Réponse :** C'est de la « soustraction d'intervalles » : partir des intervalles libres, retirer les occupés, puis découper
le reste en créneaux réservables. Algorithme : (1) valider et **normaliser** la liste des occupés : écarter les annulés, trier
par début et **fusionner les intervalles qui se chevauchent ou se touchent** (voir [Coding Q20](coding.md#merge-overlapping-intervals-solution-change)) pour que le
balayage soit simple ; (2) garder un curseur au début de la journée ; pour chaque intervalle occupé borné à la fenêtre de
travail, si `busy.start > cursor` alors `[cursor, busy.start)` est un trou libre ; avancer le curseur à `max(cursor,
busy.end)` ; après la boucle ajouter le trou final `[cursor, dayEnd)` ; (3) pour chaque trou, produire des créneaux de la
durée demandée (par ex. 20 min) tous les `step` minutes, tant que `slotEnd <= gap.end`, en respectant éventuellement des
marges et un préavis minimal. Temps O(n log n) pour le tri plus O(n + s) pour le balayage (s = créneaux produits). Décisions à
énoncer : intervalles semi-ouverts pour que des rendez-vous consécutifs soient acceptés, **fuseaux horaires et heure d'été**
(calculer dans le fuseau du praticien : un jour de passage à l'heure d'été a une heure manquante, un jour de retour à l'heure
d'hiver une heure répétée, donc `ZonedDateTime`), pauses déjeuner comme intervalles occupés supplémentaires, et comportement
quand des rendez-vous dépassent des horaires de travail. Dites aussi comment cela passe à l'échelle : précalculer par jour et
mettre brièvement en cache, mais revalider à la réservation (voir [Persistence Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)).

**Exemple :**

```java
record Interval(Instant start, Instant end) {}

static List<Interval> freeSlots(Interval workDay, List<Interval> busy, Duration slot, Duration step) {
    List<Interval> merged = merge(busy.stream()
        .filter(b -> b.end().isAfter(workDay.start()) && b.start().isBefore(workDay.end()))
        .sorted(Comparator.comparing(Interval::start)).toList());

    List<Interval> gaps = new ArrayList<>();
    Instant cursor = workDay.start();
    for (Interval b : merged) {
        if (b.start().isAfter(cursor)) gaps.add(new Interval(cursor, min(b.start(), workDay.end())));
        cursor = max(cursor, b.end());
    }
    if (cursor.isBefore(workDay.end())) gaps.add(new Interval(cursor, workDay.end()));

    List<Interval> slots = new ArrayList<>();
    for (Interval g : gaps)
        for (Instant s = g.start(); !s.plus(slot).isAfter(g.end()); s = s.plus(step))
            slots.add(new Interval(s, s.plus(slot)));
    return slots;
}
// 09:00-12:00, occupés 09:00-10:00 et 10:00-10:30 (fusionnés en 09:00-10:30), créneaux de 20 min toutes les 20 min :
// 10:30-10:50, 10:50-11:10, 11:10-11:30, 11:30-11:50
```

**Pourquoi c'est un piège :** oublier de fusionner les intervalles occupés (le curseur recule alors), ignorer les fuseaux
horaires, des écarts d'un aux bornes de la journée, et renvoyer des créneaux qui chevauchent le rendez-vous suivant parce que
le test de fin était `<` au lieu de `<=`. Testez : aucun rendez-vous, journée complète, rendez-vous commençant avant la
journée ou finissant après, rendez-vous consécutifs.

#### Q22. Traiter un très grand flux d'événements (plus gros que la mémoire) et calculer des statistiques ou le top K. {#process-very-large-stream-events}
**Réponse :** La contrainte est la mémoire, donc la réponse est **ne jamais tout charger** : lire de façon incrémentale et ne
garder que des agrégats. Posez d'abord les questions : que calcule-t-on (comptes par clé, nombre de valeurs distinctes, top K,
percentiles, déduplication) ? L'ordre est-il garanti ? Est-ce un fichier ponctuel ou un flux vivant non borné ? Techniques :
(1) **lecture en flux** : `Files.lines(path)` ou un `BufferedReader` (paresseux, à fermer avec try-with-resources), un
consommateur Kafka, ou un `ResultSet` JDBC avec une taille de fetch / curseur côté serveur, jamais `readAllLines()` ; (2)
**agrégats courants** en mémoire O(1) par élément : compte, somme, min, max, moyenne/variance (Welford) ; (3) **structures
bornées** : top K avec un min-heap de taille K (temps O(n log K), mémoire O(K), voir [Coding Q10](coding.md#heap-right-tool-solve-top)) ; (4) **maps
bornées par la cardinalité** : compter par utilisateur convient si le nombre d'utilisateurs tient en mémoire ; sinon,
**partitionner par hachage** (regroupement externe en N fichiers, traiter chacun) ou utiliser des sketches approximatifs
(HyperLogLog pour les distincts, Count-Min Sketch pour les éléments fréquents, t-digest pour les percentiles) en échangeant de
la précision contre une mémoire fixe ; (5) **dédupliquer avec un espace de clés non borné** exige un filtre de Bloom (faux
positifs, pas de faux négatifs) ou une fenêtre temporelle ; (6) **paralléliser par partition**, pas en partageant une map
(agrégats par partition fusionnés à la fin) ; (7) **contre-pression** pour les flux vivants (files bornées) et
**points de reprise** pour qu'un plantage ne reparte pas de zéro ; (8) **tri/fusion externe** quand il faut vraiment un ordre
global. Énoncez la complexité en fonction de n (événements) et k (clés distinctes). Testez avec un gros fichier généré et un
`-Xmx` réduit pour prouver que la mémoire reste plate.

**Exemple :**

```java
// Top 3 des clients par nombre d'événements dans un énorme CSV : O(n) en temps, O(clients distincts + K) en mémoire.
static List<Map.Entry<String, Long>> topK(Path file, int k) throws IOException {
    Map<String, Long> counts = new HashMap<>();
    try (Stream<String> lines = Files.lines(file)) {                 // paresseux : une seule ligne en mémoire à la fois
        lines.skip(1)
             .map(l -> l.split(",", -1)[0])                          // identifiant client
             .forEach(id -> counts.merge(id, 1L, Long::sum));
    }
    PriorityQueue<Map.Entry<String, Long>> heap = new PriorityQueue<>(Map.Entry.comparingByValue());
    for (var e : counts.entrySet()) {
        heap.offer(e);
        if (heap.size() > k) heap.poll();                            // évincer le plus petit
    }
    List<Map.Entry<String, Long>> result = new ArrayList<>(heap);
    result.sort(Map.Entry.<String, Long>comparingByValue().reversed());
    return result;
}
```

**Pourquoi c'est un piège :** `Files.readAllLines`, collecter dans une liste « juste pour trier », ou `parallel()` sur une
`HashMap` partagée échouent tous à grande échelle (OOM ou comptes faux). De plus, un stream issu de `Files.lines` doit être
fermé, sinon le descripteur de fichier fuit.

#### Q23. Comment aborder un exercice pratique « refactorez ce code » ou « revoyez cette pull request » ? {#approach-practical-refactor-code-review}
**Réponse :** Les entretiens seniors remplacent de plus en plus les énigmes par du code réaliste. Lisez tout d'abord et
dites ce que fait le code. Puis classez les problèmes par impact : **exactitude** (bugs, conditions de course,
transaction manquante, mauvaise égalité), **sécurité** (injection, autorisation manquante, secrets), **fiabilité**
(fuites de ressources, requêtes non bornées, absence de timeouts), puis **conception et lisibilité** (méthodes longues,
responsabilités mélangées, nommage). Proposez de petites étapes sûres : ajoutez un test qui fige le comportement
actuel, puis refactorez. Pour une revue, rédigez vos commentaires comme pour un collègue : le problème, pourquoi il
compte, et une suggestion concrète, en séparant « à corriger » de « détail ».

#### Q24. Calculez les disponibilités d'un praticien sur les 7 prochains jours à partir d'ouvertures hebdomadaires récurrentes et de rendez-vous réservés. {#compute-practitioner-availabilities-next-7}
**Réponse :** C'est le kata classique des plateformes de prise de rendez-vous, souvent donné en take-home ou en pair programming. L'entrée est une liste d'événements : des **ouvertures** (ponctuelles, ou récurrentes chaque semaine à partir de leur date de début) et des **rendez-vous**. La sortie donne, pour chacun des 7 jours à partir d'une date, la liste des créneaux libres de 30 minutes. Algorithme par jour : (1) garder les ouvertures qui **ont lieu ce jour-là** : une ouverture ponctuelle à cette date, ou une ouverture hebdomadaire du même jour de la semaine dont la première occurrence n'est pas postérieure au jour ; (2) découper chaque ouverture en créneaux `[t, t + 30 min)` tant que `t + 30 min <= fin` ; (3) retirer chaque créneau qui **chevauche** un rendez-vous du jour (`slot.start < appt.end && slot.end > appt.start`, intervalles semi-ouverts) ; (4) dédoublonner et trier. Complexité O(D × (O + S × A)) pour D jours, O ouvertures, S créneaux, A rendez-vous. C'est suffisant pour un agenda. Ne mentionnez la version plus rapide (trier les rendez-vous et balayer, voir [Coding Q21](coding.md#given-practitioner-working-hours-existing)) que si on vous la demande. En pair programming, commencez par les cas de test, écrivez la version la plus simple, puis refactorez : on observe votre méthode plus que le code final.

**Exemple :**

```java
enum Kind { OPENING, APPOINTMENT }
record Event(Kind kind, LocalDateTime start, LocalDateTime end, boolean weeklyRecurring) {}
record DayAvailability(LocalDate date, List<LocalTime> slots) {}

static boolean occursOn(Event e, LocalDate day) {
    return e.start().toLocalDate().equals(day) ||
        (e.weeklyRecurring() && e.start().getDayOfWeek() == day.getDayOfWeek() && !e.start().toLocalDate().isAfter(day));
}

static List<DayAvailability> availabilities(LocalDate from, List<Event> events, int days, Duration slot) {
    List<DayAvailability> result = new ArrayList<>();
    for (int offset = 0; offset < days; offset++) {
        LocalDate day = from.plusDays(offset);
        List<Event> booked = events.stream()
            .filter(e -> e.kind() == Kind.APPOINTMENT && e.start().toLocalDate().equals(day)).toList();
        TreeSet<LocalDateTime> free = new TreeSet<>();                       // dédoublonnage + tri
        for (Event o : events) {
            if (o.kind() != Kind.OPENING || !occursOn(o, day)) continue;
            LocalDateTime end = day.atTime(o.end().toLocalTime());
            for (LocalDateTime s = day.atTime(o.start().toLocalTime()); !s.plus(slot).isAfter(end); s = s.plus(slot)) {
                LocalDateTime start = s, stop = s.plus(slot);               // LocalDateTime : pas de retour à zéro à minuit
                if (booked.stream().noneMatch(b -> start.isBefore(b.end()) && stop.isAfter(b.start()))) free.add(start);
            }
        }
        result.add(new DayAvailability(day, free.stream().map(LocalDateTime::toLocalTime).toList()));
    }
    return result;
}

// Ouverture chaque lundi 09:00-11:00 depuis le 2026-10-05 ; rendez-vous lundi 2026-10-19 09:30-10:00.
List<Event> events = List.of(
    new Event(Kind.OPENING, LocalDateTime.parse("2026-10-05T09:00"), LocalDateTime.parse("2026-10-05T11:00"), true),
    new Event(Kind.APPOINTMENT, LocalDateTime.parse("2026-10-19T09:30"), LocalDateTime.parse("2026-10-19T10:00"), false));
assert availabilities(LocalDate.parse("2026-10-19"), events, 7, Duration.ofMinutes(30)).getFirst().slots()
    .equals(List.of(LocalTime.of(9, 0), LocalTime.of(10, 0), LocalTime.of(10, 30)));
```

**Pourquoi c'est un piège :** les bugs habituels sont d'appliquer une ouverture récurrente à des dates **antérieures** à son début, d'écrire `<` au lieu de `<=` si bien que le dernier créneau de la journée disparaît, d'ignorer les rendez-vous qui ne chevauchent qu'une partie d'un créneau, et d'utiliser l'arithmétique de `LocalTime`, qui repasse à zéro à minuit et rend la boucle infinie. Dites quels tests vous écririez : semaine vide, ouverture sans rendez-vous, rendez-vous couvrant plusieurs créneaux, rendez-vous à la fin exacte d'une ouverture, ouverture récurrente qui commence en milieu de semaine, et changement d'heure (en production, calculez dans la `ZoneId` du praticien).

## 🎯 Scénarios réels

### S1. Vous êtes bloqué à mi-parcours, et l'intervieweur se tait {#stuck-halfway-problem-interviewer-silent}
- **Symptômes :** Votre approche échoue sur un exemple, il reste dix minutes, et vous ne voyez pas la correction.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le silence est le pire signal pour l'intervieweur ; il ne peut ni aider ni valoriser un raisonnement
  qu'il n'entend pas. La cause habituelle est une hypothèse fausse sur l'entrée ou un invariant manquant.
- **Exemple :**

  ```text
  "Ma fenêtre casse sur 'abba' parce que left recule quand je vois le second 'a'.
   L'invariant devrait être : left ne fait qu'augmenter. Donc left = max(left, last[c] + 1)."
  ```

- **Résolution :** Dites où vous en êtes, revenez à l'exemple qui échoue et déroulez-le à voix haute, énoncez
  l'invariant attendu. Si vous restez bloqué, proposez de faire fonctionner d'abord la force brute, puis d'optimiser.
  Acceptez les indices avec aisance : bien utiliser un indice est un signal positif.
- **Prévention :** Entraînez-vous à voix haute avec un chronomètre, énoncez toujours les invariants des fenêtres et
  des pointeurs, et gardez une solution de force brute en réserve.

</details>

### S2. Votre solution passe les exemples, mais l'intervieweur dit qu'elle est trop lente pour la vraie taille d'entrée {#solution-passes-examples-but-interviewer}
- **Symptômes :** Le code est correct sur de petites entrées ; l'intervieweur évoque n = 10⁶.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Calculez explicitement la complexité actuelle et trouvez le travail répété : une boucle imbriquée
  qui cherche, un `list.contains` ou `list.remove(0)` dans une boucle, une concaténation de chaînes, ou le recalcul du
  même sous-problème.
- **Exemple :**

  ```text
  pour chaque élément : if (list.contains(x))   -> O(n) dans O(n) = O(n²) = 1e12 pour n = 1e6
  remplacer par un HashSet                      -> O(n)
  ```

- **Résolution :** Nommez le goulet, choisissez la structure qui le rend O(1) ou O(log n) (ensemble de hachage, tas,
  ordre trié plus dichotomie, sommes préfixes, mémoïsation), et réénoncez la nouvelle complexité.
- **Prévention :** Demandez la taille de l'entrée dès le départ et choisissez la complexité cible avant de coder.

</details>

### S3. Un exercice à la maison : à quoi ressemble un rendu senior ? {#take-home-assignment-senior-submission}
- **Symptômes :** Vous recevez un take-home de 4 heures (« construisez une petite API REST avec une page React ») et
  voulez vous démarquer sans sur-ingénierie.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les relecteurs vérifient que tout se lance en une commande, que la logique centrale est correcte et
  testée, et comment vous faites et documentez vos compromis. Les fonctionnalités en plus rapportent rarement ; une
  installation cassée fait toujours perdre.
- **Exemple :**

  ```bash
  README : comment lancer (docker compose up), décisions & compromis, suites possibles, temps passé
  tests :  tests unitaires du domaine + un test d'intégration API avec Testcontainers + un test RTL
  git :    petits commits avec des messages clairs
  ```

- **Résolution :** Faites bien le périmètre demandé : couches propres, validation et gestion d'erreurs, tests
  pertinents, un README avec les décisions et les limites connues. Mentionnez sans les construire les ajouts pour la
  production (authentification, pagination, observabilité).
- **Prévention :** Bornez votre temps, clarifiez tôt par e-mail les exigences ambiguës, et lancez le projet depuis un
  clone neuf avant de le rendre.

</details>

### S4. L'intervieweur change l'exigence après votre première version {#interviewer-changes-requirement-after-finished}
- **Symptômes :** Il reste 10 minutes et votre solution suppose les contraintes d'origine.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un changement d'exigence teste votre adaptabilité, pas un échec. Identifiez quelle hypothèse (entrée triée, valeurs positives, en mémoire) la contrainte casse, et si une seule fonction en dépend.
- **Résolution :** Dites l'impact à voix haute, reformulez la nouvelle exigence, adaptez la plus petite partie (par ex. remplacer un tri par un tas, ou traiter en flux) et relancez vos exemples. Si le temps manque, décrivez l'approche et sa complexité plutôt que de coder à moitié.
- **Prévention :** Isolez les hypothèses dans de petites fonctions dès le départ et énoncez-les en clarifiant ; les changements ne touchent alors qu'un endroit.

</details>

### S5. Votre solution fonctionne, puis l'intervieweur ajoute : « Maintenant l'entrée est un fichier de logs de 200 Go » {#input-no-longer-fits-memory}
- **Symptômes :** Votre compteur `HashMap<String, Integer>` de mots/IP passe les exemples ; la relance rend impossible de charger le fichier ou de garder toutes les clés en mémoire.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** L'intervieweur teste votre capacité à changer de modèle, pas de code : streaming plutôt que chargement, mémoire bornée, réponse exacte ou approchée. Demandez ce que doit être la sortie (top-10 exact ? approché suffisant ?) et quel matériel est disponible.
- **Exemple :**

  ```java
  // lire ligne à ligne, ne jamais charger le fichier
  try (var lines = Files.lines(path)) {
      lines.map(l -> l.split(" ")[0]).forEach(ip -> counts.merge(ip, 1, Integer::sum));
  }
  // trop de clés distinctes ? partitionner par ip.hashCode() % N dans N fichiers,
  // compter chaque partition en mémoire, garder un min-heap de taille k entre partitions
  ```

- **Résolution :** Déroulez l'échelle à voix haute : streamer l'entrée (`Files.lines`) ; si les clés distinctes ne tiennent toujours pas, partitionner par hash sur disque et traiter chaque partition ; pour un top-k, un min-heap borné ; si l'approché est acceptable, citer Count-Min Sketch / HyperLogLog ; à plus grande échelle, c'est un job MapReduce/Spark.
- **Prévention :** Pour chaque exercice, préparez les trois relances classiques : entrée plus grande (streaming/partitionnement), accès concurrent (thread safety) et distribué (sharding, étape de fusion).

</details>

## 🗣️ Questions fréquentes

Questions qui reviennent souvent en entretien sur ce thème (un jeu typique, non lié à un entretien précis). Chacune a une courte réponse type : développez-la avec les sections ci-dessus et dites-la à voix haute.

#### R1. Inverser une liste simplement chaînée. {#reverse-singly-linked-list}
**Réponse :** Itérez avec trois pointeurs : `prev = null`, `cur = head` ; dans la boucle sauvegardez `next = cur.next`, posez `cur.next = prev`, avancez `prev = cur`, `cur = next` ; retournez `prev`. O(n) en temps, O(1) en espace. La version récursive coûte O(n) de pile : mentionnez le risque de profondeur.

#### R2. Les parenthèses d'une chaîne sont-elles équilibrées (`()[]{}`) ? {#brackets-string-balanced}
**Réponse :** Utilisez un `Deque<Character>` comme pile : empilez les ouvrantes ; sur une fermante, la pile doit être non vide et son sommet correspondre, sinon `false`. À la fin la pile doit être vide. O(n). Cas limites : chaîne vide, uniquement des fermantes, longueur impaire.

#### R3. Une chaîne est-elle un palindrome, en ignorant la casse et les caractères non alphanumériques ? {#string-palindrome-ignoring-case-non}
**Réponse :** Deux pointeurs `i`, `j` aux deux extrémités ; sautez les caractères où `!Character.isLetterOrDigit`, comparez en minuscules, avancez vers le centre. O(n) en temps, O(1) en espace ; ne construisez pas de copie nettoyée sauf demande.

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q1. Comment aborder un exercice de live coding ?
2. Q21. Étant donné les horaires de travail d'un praticien et ses rendez-vous existants, trouver les créneaux disponibles.
3. Q4. Quand utiliser une table de hachage pour passer de O(n²) à O(n) ? Résolvez « two sum ».
4. Q7. Que sont les patterns two pointers et sliding window ? Résolvez « plus longue sous-chaîne sans caractère répété ».
5. Q9. BFS ou DFS — quand utiliser chacun ? Résolvez « nombre d'îles ».
6. Q11. Quels pièges Java font perdre des points en live coding ?
7. Q14. Qu'est-ce que la programmation dynamique, et comment repérer un problème de DP ?
8. Q17. Implémentez un cache LRU avec `get` et `put` en O(1).
9. Q19. Concevez et codez une classe de rate limiter pour une seule instance de service.
10. S2. Votre solution passe les exemples, mais l'intervieweur dit qu'elle est trop lente pour la vraie taille d'entrée

## 📌 Cheat-sheet

### Processus

> **Pour commencer :** clarifier → exemples → force brute → plan → code → test → complexité, tout à voix haute.

- **Clarifier** — taille, vide/null, doublons, négatifs, trié ? *Demandez n d'abord, il fixe la complexité cible.*
- **Tester** — dérouler un exemple, puis vide, un seul élément, tous égaux, extrêmes.
- **Bloqué** — le dire, dérouler le cas qui échoue, énoncer l'invariant, revenir à la force brute.

### Patterns

> **Pour commencer :** associez la forme du problème à un pattern avant d'écrire du code.

- **Recherche/paires/comptages** — `HashMap`/`HashSet`, O(n).
- **Intervalle contigu** — fenêtre glissante ; **paires triées** — two pointers.
- **Réponse triée ou monotone** — dichotomie (modèle lower bound).
- **Plus court chemin, non pondéré** — BFS ; **composantes, cycles, backtracking** — DFS.
- **Top K, fusion de K, ordonnancement** — tas (`PriorityQueue`).
- **Nombre de façons/coût min/sous-séquence** — DP : état, transition, cas de base.
- **Intervalles** — trier par début, puis fusionner ; `TreeMap` pour les flux.

### Java

> **Pour commencer :** prenez la bonne collection et évitez les dépassements classiques.

- **Collections** — `ArrayDeque` (pile/file), `PriorityQueue`, `TreeMap` (floor/ceiling), `int[]` pour les compteurs.
- **Idiomes** — `merge`, `getOrDefault`, `computeIfAbsent`, `Integer.compare`, `StringBuilder`.
- **Pièges** — dépassement d'`int`, `Integer ==`, comparateurs `a - b`, profondeur de récursion, `Arrays.asList` de taille fixe.
- **Créneaux libres** — triez les rendez-vous par début, parcourez depuis le début des horaires et émettez chaque trou `>=` durée du créneau ; bornez aux horaires. *O(n log n) ; demandez pour les fuseaux, chevauchements et adjacences.*
