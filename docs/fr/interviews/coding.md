# Live coding & algorithmes

Les entretiens full-stack seniors demandent rarement des algorithmes exotiques. Ils vérifient que vous savez transformer un problème en code propre et testé tout en parlant, choisir la bonne structure de données et raisonner sur la complexité. Le fonctionnement interne des collections Java est traité dans [Java Q14](java-core-jvm.md#arraylist-linkedlist-hashmap-treemap-linkedhashmap) et [Java Q36](java-core-jvm.md#happens-inside-hashmap-put-get). Une référence pattern par pattern, avec modèles, exemples résolus et katas TDD classiques, se trouve dans [Patterns de code & katas](../notes/coding-patterns.md).

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

**Règles de calcul :** instructions en séquence, on **additionne** puis on garde le terme dominant (O(n) + O(n²) = O(n²)) ; boucles imbriquées, on **multiplie** (n × m) ; diviser le problème par 2 à chaque étape, O(log n) ; récursion, (nombre d'appels) × (travail par appel), et l'espace est la **profondeur** maximale de la pile. Exemples : `HashMap.get` et `tab[i]` en O(1), `TreeMap.get` et la dichotomie en O(log n), `ArrayList.contains` en O(n), `List.sort` en O(n log n), Fibonacci naïf et les sous-ensembles en O(2ⁿ).

Trois solutions au problème « doublons », trois compromis (voir Q5) : deux boucles imbriquées en O(n²) temps et O(1) espace ; un `HashSet` en O(n) temps et O(n) espace (on échange de la mémoire contre du temps) ; un tri puis comparaison des voisins en O(n log n), mais on modifie le tableau. La bonne réponse dépend de la mémoire disponible, du droit de modifier l'entrée et de la taille de n.

**Pourquoi c'est un piège :** les appels cachés : `list.contains` dans une boucle = O(n²) ; `String +=` dans une boucle = O(n²) (copies), d'où `StringBuilder`. Fibonacci mémoïsé est O(n) en temps **et** en espace (tableau plus pile). Le O(1) de `HashMap` suppose un bon `hashCode` ; avec beaucoup de collisions, O(log n) (buckets en arbre).

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
l'ensemble (voir [Java Q37](java-core-jvm.md#mutable-object-field-based-hashcode)).

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

#### Q7. Katas sur les chaînes : anagrammes, inverser les mots d'une phrase, compter les occurrences avec `Map.merge`, FizzBuzz. {#string-katas-anagram-reverse-words-fizzbuzz}
**Réponse :** Toutes ces solutions sont en O(n). Anagramme : comparer les longueurs, compter les caractères de `a` puis décrémenter avec ceux de `b` ; un compteur négatif signifie « pas un anagramme ». Pour des minuscules ASCII seulement, un `int[26]` indexé par `c - 'a'` est plus rapide qu'une map. Inverser les mots : `split("\\s+")` absorbe les espaces multiples. Comptage : `merge(c, 1, Integer::sum)`. FizzBuzz : tester 15 en premier.

**Exemple :**

```java
static boolean isAnagram(String a, String b) {
    if (a.length() != b.length()) return false;
    Map<Character, Integer> counts = new HashMap<>();
    for (char c : a.toCharArray()) counts.merge(c, 1, Integer::sum);
    for (char c : b.toCharArray()) {
        if (counts.merge(c, -1, Integer::sum) < 0) return false;
    }
    return true;                                  // même longueur et aucun compteur négatif : tous à zéro
}

static String reverseWords(String s) {
    List<String> words = Arrays.asList(s.trim().split("\\s+"));  // \\s+ : absorbe les espaces multiples
    Collections.reverse(words);
    return String.join(" ", words);
}

static Map<Character, Integer> countChars(String s) {
    Map<Character, Integer> counts = new TreeMap<>();            // TreeMap : sortie triée, pratique au tableau
    for (char c : s.toCharArray()) counts.merge(c, 1, Integer::sum);
    return counts;
}
// En stream : s.chars().mapToObj(c -> (char) c).collect(groupingBy(identity(), counting()))  → Map<Character, Long>

static String fizzBuzz(int i) {
    if (i % 15 == 0) return "FizzBuzz";           // tester 15 en premier, sinon on renvoie "Fizz"
    if (i % 3 == 0) return "Fizz";
    if (i % 5 == 0) return "Buzz";
    return String.valueOf(i);
}
```

#### Q8. Que sont les patterns two pointers et sliding window ? Résolvez « plus longue sous-chaîne sans caractère répété ». {#two-pointer-sliding-window-patterns}
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

#### Q9. Katas sur les tableaux : sous-tableau de somme maximale (Kadane), rotation, fusion de deux tableaux triés, élément majoritaire. {#array-katas-kadane-rotation-merge-majority}
**Réponse :** **Kadane** : à chaque élément, prolonger le sous-tableau courant ou repartir d'ici, O(n). **Rotation** : triple inversion (tout, puis les k premiers, puis le reste), O(n) en temps et O(1) en mémoire. **Fusion** de deux tableaux triés : deux indices, O(n + m). **Élément majoritaire** : vote de Boyer-Moore, O(n) et O(1). Si l'existence d'un majoritaire n'est pas garantie, faire une seconde passe pour compter le candidat. La solution naïve, une `HashMap` de compteurs, est en O(n) mémoire : la donner d'abord, puis optimiser.

**Exemple :**

```java
static int maxSubarray(int[] a) {                 // Kadane, O(n), tableau non vide
    int best = a[0], cur = a[0];
    for (int i = 1; i < a.length; i++) {
        cur = Math.max(a[i], cur + a[i]);          // prolonger le sous-tableau courant ou repartir d'ici
        best = Math.max(best, cur);
    }
    return best;                                  // partir de a[0] et non de 0 : correct si tout est négatif
}

static void rotateRight(int[] a, int k) {         // triple inversion : O(n) temps, O(1) mémoire
    int n = a.length;
    if (n == 0) return;
    k %= n;                                       // piège : k peut être plus grand que n
    reverse(a, 0, n - 1);
    reverse(a, 0, k - 1);
    reverse(a, k, n - 1);
}
private static void reverse(int[] a, int i, int j) { while (i < j) swap(a, i++, j--); }  // swap : voir Tris

static int[] mergeSorted(int[] a, int[] b) {      // O(n + m)
    int[] out = new int[a.length + b.length];
    int i = 0, j = 0, k = 0;
    while (i < a.length && j < b.length) out[k++] = a[i] <= b[j] ? a[i++] : b[j++];
    while (i < a.length) out[k++] = a[i++];
    while (j < b.length) out[k++] = b[j++];
    return out;
}

static int majority(int[] a) {                    // Boyer-Moore : O(n), O(1)
    int candidate = 0, count = 0;
    for (int x : a) {
        if (count == 0) candidate = x;
        count += x == candidate ? 1 : -1;
    }
    return candidate;                             // valable seulement si un élément apparaît plus de n/2 fois
}
```

#### Q10. Comment écrire une recherche dichotomique sans erreur d'un indice ? {#write-binary-search-off-one}
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

#### Q11. Implémentez un tri à bulles, un merge sort et un quicksort, et comparez leur complexité et leur stabilité. {#sorting-bubble-merge-quick-sort}
**Réponse :** À savoir écrire sur papier en 15 min. Le **tri à bulles** (O(n²), stable, en place) sert surtout à savoir l'expliquer ; avec un drapeau `swapped` il est O(n) sur un tableau déjà trié. Le **merge sort** coupe en deux, trie chaque moitié et fusionne : O(n log n) dans tous les cas, **stable**, mais O(n) de mémoire. Le **quicksort** partitionne autour d'un pivot : O(n log n) en moyenne, **O(n²)** dans le pire cas, en place (O(log n) de pile), **non stable** ; un pivot aléatoire évite le pire cas sur un tableau déjà trié. `Arrays.sort(int[])` utilise un dual-pivot quicksort (la stabilité n'a pas de sens pour des primitifs) ; `Arrays.sort(Object[])` et `List.sort` utilisent TimSort, stable, parce que deux objets égaux pour le comparateur restent distinguables.

**Exemple :**

```java
static void bubbleSort(int[] a) {
    for (int end = a.length - 1; end > 0; end--) {
        boolean swapped = false;
        for (int i = 0; i < end; i++) {
            if (a[i] > a[i + 1]) { swap(a, i, i + 1); swapped = true; }
        }
        if (!swapped) return;                     // déjà trié : O(n) dans le meilleur cas
    }
}

static void mergeSort(int[] a) {
    if (a.length > 1) mergeSort(a, new int[a.length], 0, a.length - 1);
}
private static void mergeSort(int[] a, int[] tmp, int lo, int hi) {
    if (lo >= hi) return;
    int mid = lo + (hi - lo) / 2;                 // pas (lo + hi) / 2 : débordement d'int
    mergeSort(a, tmp, lo, mid);
    mergeSort(a, tmp, mid + 1, hi);
    int i = lo, j = mid + 1, k = lo;
    while (i <= mid && j <= hi) tmp[k++] = a[i] <= a[j] ? a[i++] : a[j++];  // <= : garantit la stabilité
    while (i <= mid) tmp[k++] = a[i++];
    while (j <= hi) tmp[k++] = a[j++];
    System.arraycopy(tmp, lo, a, lo, hi - lo + 1);
}

static void quickSort(int[] a) {
    quickSort(a, 0, a.length - 1);
}
private static void quickSort(int[] a, int lo, int hi) {
    if (lo >= hi) return;
    swap(a, ThreadLocalRandom.current().nextInt(lo, hi + 1), hi);  // pivot aléatoire : évite O(n²) sur un tableau déjà trié
    int pivot = a[hi], i = lo;
    for (int j = lo; j < hi; j++) if (a[j] < pivot) swap(a, i++, j);  // partition de Lomuto
    swap(a, i, hi);
    quickSort(a, lo, i - 1);
    quickSort(a, i + 1, hi);
}

static void swap(int[] a, int i, int j) { int t = a[i]; a[i] = a[j]; a[j] = t; }
```

| Tri | Moyen | Pire cas | Mémoire | Stable |
|---|---|---|---|---|
| Bulles | O(n²) | O(n²) | O(1) | oui |
| Fusion | O(n log n) | O(n log n) | O(n) | oui |
| Rapide | O(n log n) | O(n²) | O(log n) (pile d'appels) | non |

#### Q12. Écrivez factorielle et Fibonacci (naïf, mémoïsé, itératif), puis la puissance rapide. {#recursion-factorial-fibonacci-fast-power}
**Réponse :** Fibonacci naïf recalcule les mêmes sous-problèmes : O(2ⁿ) en temps. La **mémoïsation** le ramène à O(n) en temps et O(n) en mémoire (tableau plus pile) ; la version **itérative** à O(n) en temps et O(1) en mémoire. La **puissance rapide** divise l'exposant par 2 à chaque appel : O(log n). C'est le chemin naturel vers la programmation dynamique (voir Q14).

**Exemple :**

```java
static long factorial(int n) {
    if (n < 0) throw new IllegalArgumentException("n < 0");
    return n <= 1 ? 1 : n * factorial(n - 1);    // déborde au-delà de 20! : passer à BigInteger
}

static long fibNaive(int n) { return n < 2 ? n : fibNaive(n - 1) + fibNaive(n - 2); }  // O(2ⁿ) : recalcule tout

static long fibMemo(int n) { return fibMemo(n, new long[n + 1]); }
private static long fibMemo(int n, long[] memo) {
    if (n < 2) return n;
    if (memo[n] != 0) return memo[n];
    return memo[n] = fibMemo(n - 1, memo) + fibMemo(n - 2, memo);  // O(n) temps, O(n) mémoire
}

static long fibIter(int n) {
    long a = 0, b = 1;
    for (int i = 0; i < n; i++) { long t = a + b; a = b; b = t; }
    return a;                                     // O(n) temps, O(1) mémoire
}

static long power(long x, int n) {                // x^n en O(log n), n >= 0
    if (n == 0) return 1;
    long half = power(x, n / 2);
    return n % 2 == 0 ? half * half : half * half * x;
}
```

**Pourquoi c'est un piège :** une récursion trop profonde provoque une `StackOverflowError` ; Java n'optimise pas la récursion terminale, d'où la version itérative.

#### Q13. BFS ou DFS — quand utiliser chacun ? Résolvez « nombre d'îles ». {#bfs-dfs-each-solve-number}
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

#### Q14. Parcours d'un arbre binaire (préfixe, infixe, suffixe, récursifs et itératifs), hauteur, validation d'un BST et plus petit ancêtre commun. {#binary-tree-traversals-height-bst-lca}
**Réponse :** Préfixe = racine, gauche, droite ; infixe = gauche, racine, droite (ordre **trié** pour un BST) ; suffixe = gauche, droite, racine. La version itérative remplace la pile d'appels par un `ArrayDeque` (le suffixe s'obtient en faisant un préfixe « racine, droite, gauche » puis en retournant le résultat). Toutes ces opérations sont en O(n). Pour valider un BST, on propage des **bornes** (min, max) vers le bas ; le plus petit ancêtre commun (LCA) est le premier nœud qui voit p et q de part et d'autre.

**Exemple :**

```java
record Node(int val, Node left, Node right) {
    Node(int val) { this(val, null, null); }
}

static void preorder(Node n, List<Integer> out) {      // racine, gauche, droite
    if (n == null) return;
    out.add(n.val());
    preorder(n.left(), out);
    preorder(n.right(), out);
}

static void inorder(Node n, List<Integer> out) {       // gauche, racine, droite : ordre trié pour un BST
    if (n == null) return;
    inorder(n.left(), out);
    out.add(n.val());
    inorder(n.right(), out);
}

static void postorder(Node n, List<Integer> out) {     // gauche, droite, racine
    if (n == null) return;
    postorder(n.left(), out);
    postorder(n.right(), out);
    out.add(n.val());
}

static List<Integer> preorderIterative(Node root) {
    List<Integer> out = new ArrayList<>();
    Deque<Node> stack = new ArrayDeque<>();
    if (root != null) stack.push(root);
    while (!stack.isEmpty()) {
        Node n = stack.pop();
        out.add(n.val());
        if (n.right() != null) stack.push(n.right());   // droite d'abord, pour dépiler la gauche en premier
        if (n.left() != null) stack.push(n.left());
    }
    return out;
}

static List<Integer> inorderIterative(Node root) {
    List<Integer> out = new ArrayList<>();
    Deque<Node> stack = new ArrayDeque<>();
    Node cur = root;
    while (cur != null || !stack.isEmpty()) {
        while (cur != null) { stack.push(cur); cur = cur.left(); }  // descendre tout à gauche
        cur = stack.pop();
        out.add(cur.val());
        cur = cur.right();
    }
    return out;
}

static List<Integer> postorderIterative(Node root) {    // préfixe inversé (racine, droite, gauche), puis on retourne
    List<Integer> out = new ArrayList<>();
    Deque<Node> stack = new ArrayDeque<>();
    if (root != null) stack.push(root);
    while (!stack.isEmpty()) {
        Node n = stack.pop();
        out.add(n.val());
        if (n.left() != null) stack.push(n.left());
        if (n.right() != null) stack.push(n.right());
    }
    Collections.reverse(out);
    return out;
}

static int height(Node n) { return n == null ? 0 : 1 + Math.max(height(n.left()), height(n.right())); }

static boolean isBst(Node n) { return isBst(n, Long.MIN_VALUE, Long.MAX_VALUE); }
private static boolean isBst(Node n, long min, long max) {  // bornes exclusives, en long pour accepter Integer.MIN_VALUE
    if (n == null) return true;
    if (n.val() <= min || n.val() >= max) return false;
    return isBst(n.left(), min, n.val()) && isBst(n.right(), n.val(), max);
}

static Node lca(Node root, Node p, Node q) {           // arbre binaire quelconque, O(n)
    if (root == null || root == p || root == q) return root;
    Node l = lca(root.left(), p, q), r = lca(root.right(), p, q);
    if (l != null && r != null) return root;           // p et q sont de part et d'autre
    return l != null ? l : r;
}
```

**Pourquoi c'est un piège :** pour `isBst`, comparer chaque nœud seulement à ses enfants directs est faux (un petit-enfant peut violer la borne de la racine). Pour un BST, le LCA se trouve en O(h) : descendre à gauche si p et q sont plus petits que le nœud, à droite s'ils sont plus grands, sinon le nœud courant est la réponse.

#### Q15. Quand un tas est-il le bon outil ? Résolvez « top K éléments les plus fréquents ». {#heap-right-tool-solve-top}
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

#### Q16. Listes chaînées : détecter un cycle (Floyd), trouver le milieu, fusionner deux listes triées. {#linked-list-cycle-middle-merge}
**Réponse :** **Floyd** (lièvre et tortue) : deux pointeurs, l'un avance de 1 et l'autre de 2 ; s'ils se rejoignent, il y a un cycle. O(n) en temps, O(1) en mémoire. Le même schéma donne le **milieu** (quand le rapide atteint la fin, le lent est au milieu). Pour la **fusion**, un nœud sentinelle évite le cas particulier de la tête. Alternative à Floyd : stocker les nœuds visités dans un `HashSet`, plus simple mais en O(n) mémoire ; c'est la réponse naïve à donner en premier.

**Exemple :**

```java
static final class ListNode {
    int val;
    ListNode next;
    ListNode(int val) { this.val = val; }
}

static boolean hasCycle(ListNode head) {          // Floyd (lièvre et tortue) : O(n), O(1)
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) return true;
    }
    return false;
}

static ListNode middle(ListNode head) {           // longueur paire : renvoie le second milieu
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }
    return slow;
}

static ListNode mergeLists(ListNode a, ListNode b) {
    ListNode dummy = new ListNode(0), tail = dummy;   // nœud sentinelle : pas de cas particulier pour la tête
    while (a != null && b != null) {
        if (a.val <= b.val) { tail.next = a; a = a.next; } else { tail.next = b; b = b.next; }
        tail = tail.next;
    }
    tail.next = a != null ? a : b;
    return dummy.next;
}
```

Voir aussi R1 pour inverser une liste.

#### Q17. Implémentez une file avec deux piles, et une pile qui renvoie son minimum en O(1) (min-stack). {#stack-queue-two-stack-queue-min-stack}
**Réponse :** **File à deux piles** : on empile dans `in`, et on ne transfère vers `out` que lorsque `out` est vide ; chaque élément passe une seule fois de l'une à l'autre, donc O(1) **amorti**. **Min-stack** : une seconde pile ne garde que les minima successifs ; on y empile quand `x <=` au minimum courant (le `<=` gère les doublons du minimum). Utiliser `ArrayDeque` plutôt que `Stack`, synchronisée et héritée de `Vector`.

**Exemple :**

```java
static final class TwoStackQueue<E> {
    private final Deque<E> in = new ArrayDeque<>(), out = new ArrayDeque<>();
    void offer(E e) { in.push(e); }
    E poll() {
        if (out.isEmpty()) while (!in.isEmpty()) out.push(in.pop());  // transfert seulement quand out est vide
        return out.poll();                                              // null si la file est vide
    }
}

static final class MinStack {
    private final Deque<Integer> stack = new ArrayDeque<>(), mins = new ArrayDeque<>();
    void push(int x) {
        stack.push(x);
        if (mins.isEmpty() || x <= mins.peek()) mins.push(x);   // <= : gère les doublons du minimum
    }
    int pop() {
        int x = stack.pop();
        if (x == mins.peek()) mins.pop();
        return x;
    }
    int min() { return mins.peek(); }                           // O(1)
}
```

## 🟡 Pièges seniors

### Questions

#### Q18. Quels pièges Java font perdre des points en live coding ? {#java-pitfalls-cost-candidates-points}
**Réponse :** Le **dépassement d'entier** (`(lo + hi) / 2`, sommes de grands entiers : utilisez `long`) ; comparer
des nombres boxés avec `==` (`Integer` au-delà de 127, voir [Java Q26](java-core-jvm.md#autoboxing-trap-integer)) ; un comparateur écrit
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

#### Q19. Regrouper des rendez-vous par médecin et par date avec les streams. {#group-appointments-doctor-date-streams}
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
[Java Q31](java-core-jvm.md#common-ways-stream-pipeline-goes).

#### Q20. Détecter des réservations qui se chevauchent. {#detect-overlapping-bookings}
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

#### Q21. Qu'est-ce que la programmation dynamique, et comment repérer un problème de DP ? {#dynamic-programming-spot-dp-problem}
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

#### Q22. Implémenter un compteur thread-safe. {#implement-thread-safe-counter}
**Réponse :** `count++` fait trois étapes (lire, ajouter, écrire), donc deux threads peuvent lire 5 et écrire tous deux 6 : une
mise à jour perdue. Options, de la plus simple à la plus scalable : (1) des méthodes **`synchronized`** ou un `ReentrantLock` :
correct, mais les threads font la queue à chaque appel ; (2) **`AtomicLong`/`AtomicInteger`** : `incrementAndGet()` utilise un
compare-and-swap matériel, sans verrou, et c'est le bon choix par défaut pour un compteur dont on lit aussi la valeur ; sous
très forte contention la boucle CAS réessaie beaucoup ; (3) **`LongAdder`** : répartit les mises à jour sur des cellules
internes et les additionne dans `sum()`, bien plus rapide sous forte contention en écriture (métriques, compteurs de
requêtes), mais `sum()` n'est pas un instantané atomique et il n'offre pas de compare-and-set, donc il est inadapté pour
« incrémenter *seulement si* sous une limite ». (4) Ne pas partager du tout : des compteurs par thread fusionnés à la fin. Un
`volatile long` seul **ne suffit pas** : il garantit la visibilité mais pas l'atomicité de `++` (voir
[Java Q41](java-core-jvm.md#real-synchronized-volatile)). Pour un compteur borné (limite de débit, « maximum 3 réservations »), utilisez une boucle CAS
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

#### Q23. Implémenter une logique de nouvelle tentative (retry) avec un nombre maximal de tentatives. {#implement-retry-logic-maximum-number}
**Réponse :** Un utilitaire de retry reçoit une opération, un nombre maximal de tentatives, une politique de délai et un
prédicat indiquant quels échecs sont rejouables. Décisions à énoncer : (1) **ne rejouer que les erreurs transitoires**
(timeouts, `503`, connexion coupée, victime de deadlock), jamais les erreurs de validation ou `4xx`, et **seulement les
opérations idempotentes**, ou protégées par une clé d'idempotence, sinon un retry après une réponse perdue duplique un
paiement ou une réservation (voir [Full Stack Q11](fullstack-devops-k8s.md#idempotency-rest-api-post-need)) ; (2) **le borner** : un nombre maximal de
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
[Spring Q39](spring-architecture.md#circuit-breaker-pattern-service-need)).

#### Q24. Implémentez un cache LRU avec `get` et `put` en O(1). {#implement-lru-cache-o-1}
**Réponse :** Il faut une recherche en O(1) (une table de hachage) et des opérations « passer en plus récent » et
« évincer le plus ancien » en O(1) (une liste doublement chaînée). En Java, `LinkedHashMap` avec `accessOrder = true`
et une redéfinition de `removeEldestEntry` fournit exactement cela en quelques lignes. Les intervieweurs demandent
souvent ensuite de le construire à la main (map de clé vers nœud, plus une liste doublement chaînée avec des
sentinelles en tête et en queue) : soyez prêt pour les deux. La sûreté multi-thread et les compromis de mémoire bornée
sont traités dans [Java Q39](java-core-jvm.md#design-thread-safe-bounded-lru).

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

#### Q25. Comment tester votre code pendant l'entretien ? {#test-code-during-interview}
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

#### Q26. Concevez et codez une classe de rate limiter pour une seule instance de service. {#design-code-rate-limiter-class}
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

#### Q27. Fusionnez des intervalles qui se chevauchent ; comment la solution change-t-elle pour un flux d'intervalles ? {#merge-overlapping-intervals-solution-change}
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

#### Q28. Étant donné les horaires de travail d'un praticien et ses rendez-vous existants, trouver les créneaux disponibles. {#given-practitioner-working-hours-existing}
**Réponse :** C'est de la « soustraction d'intervalles » : partir des intervalles libres, retirer les occupés, puis découper
le reste en créneaux réservables. Algorithme : (1) valider et **normaliser** la liste des occupés : écarter les annulés, trier
par début et **fusionner les intervalles qui se chevauchent ou se touchent** (voir [Coding Q27](coding.md#merge-overlapping-intervals-solution-change)) pour que le
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

#### Q29. Traiter un très grand flux d'événements (plus gros que la mémoire) et calculer des statistiques ou le top K. {#process-very-large-stream-events}
**Réponse :** La contrainte est la mémoire, donc la réponse est **ne jamais tout charger** : lire de façon incrémentale et ne
garder que des agrégats. Posez d'abord les questions : que calcule-t-on (comptes par clé, nombre de valeurs distinctes, top K,
percentiles, déduplication) ? L'ordre est-il garanti ? Est-ce un fichier ponctuel ou un flux vivant non borné ? Techniques :
(1) **lecture en flux** : `Files.lines(path)` ou un `BufferedReader` (paresseux, à fermer avec try-with-resources), un
consommateur Kafka, ou un `ResultSet` JDBC avec une taille de fetch / curseur côté serveur, jamais `readAllLines()` ; (2)
**agrégats courants** en mémoire O(1) par élément : compte, somme, min, max, moyenne/variance (Welford) ; (3) **structures
bornées** : top K avec un min-heap de taille K (temps O(n log K), mémoire O(K), voir [Coding Q15](coding.md#heap-right-tool-solve-top)) ; (4) **maps
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

#### Q30. Comment aborder un exercice pratique « refactorez ce code » ou « revoyez cette pull request » ? {#approach-practical-refactor-code-review}
**Réponse :** Les entretiens seniors remplacent de plus en plus les énigmes par du code réaliste. Lisez tout d'abord et
dites ce que fait le code. Puis classez les problèmes par impact : **exactitude** (bugs, conditions de course,
transaction manquante, mauvaise égalité), **sécurité** (injection, autorisation manquante, secrets), **fiabilité**
(fuites de ressources, requêtes non bornées, absence de timeouts), puis **conception et lisibilité** (méthodes longues,
responsabilités mélangées, nommage). Proposez de petites étapes sûres : ajoutez un test qui fige le comportement
actuel, puis refactorez. Pour une revue, rédigez vos commentaires comme pour un collègue : le problème, pourquoi il
compte, et une suggestion concrète, en séparant « à corriger » de « détail ».

#### Q31. Calculez les disponibilités d'un praticien sur les 7 prochains jours à partir d'ouvertures hebdomadaires récurrentes et de rendez-vous réservés. {#compute-practitioner-availabilities-next-7}
**Réponse :** C'est le kata classique des plateformes de prise de rendez-vous, souvent donné en take-home ou en pair programming. L'entrée est une liste d'événements : des **ouvertures** (ponctuelles, ou récurrentes chaque semaine à partir de leur date de début) et des **rendez-vous**. La sortie donne, pour chacun des 7 jours à partir d'une date, la liste des créneaux libres de 30 minutes. Algorithme par jour : (1) garder les ouvertures qui **ont lieu ce jour-là** : une ouverture ponctuelle à cette date, ou une ouverture hebdomadaire du même jour de la semaine dont la première occurrence n'est pas postérieure au jour ; (2) découper chaque ouverture en créneaux `[t, t + 30 min)` tant que `t + 30 min <= fin` ; (3) retirer chaque créneau qui **chevauche** un rendez-vous du jour (`slot.start < appt.end && slot.end > appt.start`, intervalles semi-ouverts) ; (4) dédoublonner et trier. Complexité O(D × (O + S × A)) pour D jours, O ouvertures, S créneaux, A rendez-vous. C'est suffisant pour un agenda. Ne mentionnez la version plus rapide (trier les rendez-vous et balayer, voir [Coding Q28](coding.md#given-practitioner-working-hours-existing)) que si on vous la demande. En pair programming, commencez par les cas de test, écrivez la version la plus simple, puis refactorez : on observe votre méthode plus que le code final.

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

### Tableaux, chaînes, hachage

#### R4. Trouver le deuxième plus grand nombre (ou le Nième plus haut salaire, ou le top 3). {#second-nth-highest-number-salary}
**Réponse :** Un seul passage suivant les deux plus grandes valeurs : O(n) en temps, O(1) en espace (un `Set`/tri est plus simple mais en O(n log n)). Gérer les doublons et les tableaux avec moins de 2 valeurs distinctes :

```java
static OptionalInt secondHighest(int[] a) {
    long max = Long.MIN_VALUE, second = Long.MIN_VALUE;
    for (int x : a) {
        if (x > max) { second = max; max = x; }
        else if (x < max && x > second) second = x;   // ignore les doublons du max
    }
    return second == Long.MIN_VALUE ? OptionalInt.empty() : OptionalInt.of((int) second);
}
```
Pour le **Nième plus grand** ou le **top 3** : garder un **min-heap de taille N** (`PriorityQueue`), ajouter chaque valeur et retirer la tête quand la taille dépasse N : O(n log N) ; la racine est le Nième plus grand. Avec les streams : `list.stream().distinct().sorted(Comparator.reverseOrder()).skip(n-1).findFirst()`. En SQL : `SELECT DISTINCT salary FROM emp ORDER BY salary DESC OFFSET n-1 LIMIT 1` (ou `DENSE_RANK()`).

#### R5. Trouver les éléments communs de deux listes, et supprimer les doublons avec les streams. {#common-elements-two-lists-remove-duplicates-streams}
**Réponse :** Mettre une liste dans un `HashSet` et garder les éléments de l'autre qu'il contient : O(n + m) au lieu de O(n·m) :

```java
Set<Integer> seen = new HashSet<>(a);
List<Integer> common = b.stream().filter(seen::contains).distinct().toList();
// ou : Set<Integer> r = new HashSet<>(a); r.retainAll(new HashSet<>(b));

List<Integer> unique = list.stream().distinct().toList();          // garde les premières occurrences, ordre conservé
Set<Integer> uniqueOrdered = new LinkedHashSet<>(list);            // idem sans streams
```
`distinct()` s'appuie sur `equals`/`hashCode` : les objets personnalisés doivent définir les deux. Pour trouver les valeurs *dupliquées*, utiliser `Collectors.groupingBy(identity(), counting())` et garder les comptes > 1.

#### R6. Trouver le premier caractère répété, et compter la fréquence des caractères ou des mots en conservant l'ordre d'insertion. {#first-repeated-char-character-word-frequency}
**Réponse :** Utiliser une `LinkedHashMap` pour que l'itération suive l'ordre d'insertion, et `merge` pour compter :

```java
static Character firstRepeated(String s) {
    Set<Character> seen = new HashSet<>();
    for (char c : s.toCharArray()) if (!seen.add(c)) return c;   // add() renvoie false si déjà présent
    return null;
}

Map<Character, Integer> freq = new LinkedHashMap<>();
for (char c : s.toCharArray()) freq.merge(c, 1, Integer::sum);

Map<String, Long> words = Arrays.stream(text.toLowerCase().split("\\W+"))
    .collect(Collectors.groupingBy(w -> w, LinkedHashMap::new, Collectors.counting()));
```
Tout en O(n) temps, O(k) espace pour k clés distinctes. Pour le *premier caractère non répété*, parcourir la `LinkedHashMap` et renvoyer la première entrée de compte 1.

#### R7. Group Anagrams : `["eat","tea","tan","ate","nat","bat"]`. {#group-anagrams}
**Réponse :** Les anagrammes partagent la même **clé canonique** : les lettres triées (ou une signature de 26 compteurs). Regrouper par cette clé dans une map : O(n·k log k) avec tri (k = longueur du mot), O(n·k) avec des clés de comptage.

```java
static List<List<String>> groupAnagrams(String[] words) {
    Map<String, List<String>> groups = new HashMap<>();
    for (String w : words) {
        char[] c = w.toCharArray();
        Arrays.sort(c);
        groups.computeIfAbsent(new String(c), k -> new ArrayList<>()).add(w);
    }
    return new ArrayList<>(groups.values());
}
// [[eat, tea, ate], [tan, nat], [bat]]
```
L'idée clé est de choisir une clé identique pour tous les membres d'un groupe ; un seul passage par hachage fait le reste.

#### R8. K mots les plus fréquents (par fréquence, puis ordre lexicographique). {#k-most-frequent-words}
**Réponse :** Compter avec une map, puis garder les K meilleurs avec un tas ordonné par *fréquence croissante, puis mot décroissant* pour que le « pire » soit toujours à la racine et évincé : O(n log k).

```java
static List<String> topK(String[] words, int k) {
    Map<String, Integer> cnt = new HashMap<>();
    for (String w : words) cnt.merge(w, 1, Integer::sum);

    PriorityQueue<Map.Entry<String, Integer>> pq = new PriorityQueue<>(
        Comparator.<Map.Entry<String, Integer>>comparingInt(Map.Entry::getValue)
                  .thenComparing(Map.Entry::getKey, Comparator.reverseOrder()));
    for (var e : cnt.entrySet()) { pq.add(e); if (pq.size() > k) pq.poll(); }

    LinkedList<String> res = new LinkedList<>();
    while (!pq.isEmpty()) res.addFirst(pq.poll().getKey());
    return res;
}
```
L'alternative plus simple est `sorted(parFréquenceDesc.thenComparing(naturalOrder())).limit(k)` : O(n log n), suffisant pour de petites entrées ; mentionner le tri par seaux pour O(n).

#### R9. Valider une expression avec `{`, `}` et `*` (joker) équilibrés. {#balanced-braces-with-wildcard-star}
**Réponse :** Une pile seule échoue car `*` peut valoir `{`, `}` ou rien. Suivre **l'intervalle des nombres d'ouvertures possibles** : `lo` (minimum si chaque `*` ferme) et `hi` (maximum si chaque `*` ouvre). Pour `{` les deux +1 ; pour `}` les deux −1 ; pour `*` `lo−1`, `hi+1` ; borner `lo` à 0 ; si `hi < 0`, il y a plus de fermetures que d'appariements possibles : échec. Valide ssi `lo == 0` à la fin. O(n), O(1) en espace.

```java
static boolean valid(String s) {
    int lo = 0, hi = 0;
    for (char c : s.toCharArray()) {
        if (c == '{')      { lo++; hi++; }
        else if (c == '}') { lo--; hi--; }
        else               { lo--; hi++; }          // '*'
        if (hi < 0) return false;
        lo = Math.max(lo, 0);
    }
    return lo == 0;
}
```
C'est LeetCode 678 (« Valid Parenthesis String ») avec des accolades au lieu de parenthèses.

#### R10. Convertir une expression infixe en postfixe (shunting-yard). {#infix-to-postfix-conversion}
**Réponse :** Parcourir les jetons de gauche à droite avec une **pile d'opérateurs** : les opérandes vont directement en sortie ; pour un opérateur, dépiler vers la sortie ceux de **priorité supérieure ou égale** (associatifs à gauche) puis l'empiler ; `(` est empilée ; `)` dépile jusqu'à `(`. À la fin, tout dépiler. O(n).

```java
static String toPostfix(String expr) {
    Map<Character, Integer> prec = Map.of('+',1,'-',1,'*',2,'/',2,'^',3);
    StringBuilder out = new StringBuilder();
    Deque<Character> ops = new ArrayDeque<>();
    for (char c : expr.toCharArray()) {
        if (Character.isLetterOrDigit(c)) out.append(c);
        else if (c == '(') ops.push(c);
        else if (c == ')') { while (ops.peek() != '(') out.append(ops.pop()); ops.pop(); }
        else {                                   // opérateur
            while (!ops.isEmpty() && ops.peek() != '(' && 
                   (prec.get(ops.peek()) > prec.get(c) || (prec.get(ops.peek()) == prec.get(c) && c != '^')))
                out.append(ops.pop());
            ops.push(c);
        }
    }
    while (!ops.isEmpty()) out.append(ops.pop());
    return out.toString();
}
// "a+b*(c-d)" -> "abcd-*+"
```
`^` est associatif à droite, d'où le test `c != '^'`. Évaluer le postfixe avec une seule pile d'opérandes.

#### R11. Calculer la somme des nombres pairs de 1 à 100, et le solde final par compte à partir de transactions avec `Map.merge()`. {#sum-even-numbers-final-balance-per-account}
**Réponse :** Somme des pairs : `IntStream.rangeClosed(1, 100).filter(n -> n % 2 == 0).sum()` = 2550 (ou la formule `2 · (50·51/2)`). Soldes : `merge(clé, delta, Integer::sum)` insère le delta ou l'ajoute à la valeur existante en un seul appel, sans le triptyque `containsKey`/`get`/`put` :

```java
record Tx(String account, int amount) {}

Map<String, Integer> balances = new HashMap<>();
for (Tx t : txs) balances.merge(t.account(), t.amount(), Integer::sum);
// [A:+100, B:+200, A:-50] -> {A=50, B=200}

// version stream
Map<String, Integer> b2 = txs.stream()
    .collect(Collectors.toMap(Tx::account, Tx::amount, Integer::sum));
```
Complexité O(n) en temps, O(comptes) en espace. Utiliser `BigDecimal`/centimes (`long`) pour de l'argent réel, et `ConcurrentHashMap.merge` si mis à jour par plusieurs threads.

### Exercices streams & collections

#### R12. Exercices streams : plus haut salaire par département, employés au-dessus de la moyenne, `List<Employee>` → `Map<Id, Employee>`, partition pairs/impairs, totaux par utilisateur, tri par salaire puis nom. {#streams-employee-salary-exercises}
**Réponse :** Avec `record Employee(int id, String name, String dept, String city, double salary)` :

```java
// employé le mieux payé par département
Map<String, Optional<Employee>> top = emps.stream().collect(
    groupingBy(Employee::dept, maxBy(comparingDouble(Employee::salary))));

// regrouper par département ; noms seulement
Map<String, List<String>> names = emps.stream().collect(
    groupingBy(Employee::dept, mapping(Employee::name, toList())));

// au-dessus de la moyenne
double avg = emps.stream().mapToDouble(Employee::salary).average().orElse(0);
List<Employee> rich = emps.stream().filter(e -> e.salary() > avg).toList();

// liste -> map (la fonction de fusion gère les ids dupliqués)
Map<Integer, Employee> byId = emps.stream().collect(toMap(Employee::id, identity(), (a, b) -> a));

// stats, extrêmes, partition, totaux, filtres
DoubleSummaryStatistics st = emps.stream().mapToDouble(Employee::salary).summaryStatistics(); // somme, moyenne, min, max
String longest = names.stream().max(comparingInt(String::length)).orElse("");
Map<Boolean, List<Integer>> evenOdd = nums.stream().collect(partitioningBy(n -> n % 2 == 0));
Map<Integer, Double> totalByUser = orders.stream().collect(groupingBy(Order::userId, summingDouble(Order::amount)));
List<Employee> inCity = emps.stream().filter(e -> "Paris".equals(e.city())).toList();
List<Employee> startsWithA = emps.stream().filter(e -> e.name().startsWith("A")).toList();

// tri par salaire décroissant puis nom
emps.sort(comparingDouble(Employee::salary).reversed().thenComparing(Employee::name));

// top 5 des salaires par département
Map<String, List<Double>> top5 = emps.stream().collect(groupingBy(Employee::dept,
    collectingAndThen(toList(), l -> l.stream().map(Employee::salary).sorted(reverseOrder()).limit(5).toList())));
```
Pièges à citer : `toMap` lève une exception sur les clés dupliquées sans fonction de fusion ; `maxBy` renvoie un `Optional` ; comparer les `double` avec `comparingDouble`, jamais par soustraction.

#### R13. Trier des objets `Shipment` par `packageCost` croissant, puis `city`. {#comparator-chaining-shipments-package-cost-city}
**Réponse :** Chaîner les comparateurs : `Comparator.comparingDouble(Shipment::packageCost).thenComparing(Shipment::city)` ; `list.sort(cmp)`.

```java
record Shipment(String city, double packageCost) {}

Comparator<Shipment> cmp = Comparator
    .comparingDouble(Shipment::packageCost)                 // coût croissant
    .thenComparing(Shipment::city, String.CASE_INSENSITIVE_ORDER);
shipments.sort(cmp);
// coût décroissant, ville croissante : comparingDouble(...).reversed().thenComparing(...)
```
Variantes null-safe : `Comparator.nullsLast(...)`. Ne jamais écrire `(a, b) -> (int)(a.cost - b.cost)` : cela tronque les fractions et peut déborder, donc viole le contrat du comparateur.

### Listes, tas, graphes & concurrence

#### R14. Fusionner K listes triées, trouver le Kième plus grand dans un flux, et la médiane d'un flux de données. {#merge-k-sorted-lists-kth-largest-median-stream}
**Réponse :** Les trois utilisent des **tas**. **Fusion de K listes triées** : un min-heap contient la tête courante de chaque liste ; extraire la plus petite, l'ajouter, empiler son successeur : O(N log K) pour N nœuds au total.

```java
ListNode mergeK(ListNode[] lists) {
    PriorityQueue<ListNode> pq = new PriorityQueue<>(Comparator.comparingInt(n -> n.val));
    for (ListNode l : lists) if (l != null) pq.add(l);
    ListNode dummy = new ListNode(0), tail = dummy;
    while (!pq.isEmpty()) {
        ListNode n = pq.poll();
        tail = tail.next = n;
        if (n.next != null) pq.add(n.next);
    }
    return dummy.next;
}
```
**Kième plus grand dans un flux** : garder un **min-heap de taille k** ; `add(x)` : empiler, et si la taille dépasse k retirer la tête ; la racine est la réponse : O(log k) par élément. **Médiane d'un flux** : deux tas, un **max-heap pour la moitié basse** et un **min-heap pour la moitié haute**, de tailles différant d'au plus 1 ; ajouter à la moitié basse, déplacer son maximum vers la haute, rééquilibrer ; la médiane est la racine du plus gros tas ou la moyenne des deux racines : O(log n) l'insertion, O(1) la médiane.

#### R15. Détecter un cycle dans un graphe orienté, et résoudre Word Ladder. {#detect-cycle-directed-graph-word-ladder}
**Réponse :** **Cycle dans un graphe orienté** : DFS à trois couleurs (0 = non visité, 1 = sur le chemin courant, 2 = terminé) ; rencontrer un nœud d'état 1 signifie un **arc retour**, donc un cycle. (Alternative : tri topologique de Kahn : si moins de V nœuds sont traités, il y a un cycle.) O(V+E).

```java
boolean hasCycle(Map<Integer, List<Integer>> g, int n) {
    int[] state = new int[n];
    for (int i = 0; i < n; i++) if (state[i] == 0 && dfs(g, i, state)) return true;
    return false;
}
boolean dfs(Map<Integer, List<Integer>> g, int u, int[] s) {
    s[u] = 1;
    for (int v : g.getOrDefault(u, List.of())) {
        if (s[v] == 1) return true;
        if (s[v] == 0 && dfs(g, v, s)) return true;
    }
    s[u] = 2;
    return false;
}
```
**Word Ladder** (transformation la plus courte, une lettre à la fois, chaque mot dans un dictionnaire) est un **plus court chemin dans un graphe non pondéré → BFS** : depuis le mot de départ, générer toutes les mutations d'une lettre, garder celles du dictionnaire (en les retirant pour les marquer visitées) et compter les niveaux BFS jusqu'à la cible ; renvoyer 0 si elle n'est jamais atteinte. Un BFS bidirectionnel divise la recherche par deux. O(N · L · 26) pour N mots de longueur L.

#### R16. Résoudre le task scheduler et Minimum Platforms (glouton). {#task-scheduler-minimum-platforms-greedy}
**Réponse :** **Minimum Platforms** : trier séparément arrivées et départs et balayer avec deux pointeurs ; chaque arrivée avant le premier départ non terminé exige une nouvelle voie, sinon une voie se libère. Le maximum de trains simultanés est la réponse. O(n log n).

```java
static int minPlatforms(int[] arr, int[] dep) {
    Arrays.sort(arr); Arrays.sort(dep);
    int need = 0, best = 0, i = 0, j = 0;
    while (i < arr.length) {
        if (arr[i] <= dep[j]) { need++; i++; best = Math.max(best, need); }
        else { need--; j++; }
    }
    return best;
}
```
**Task scheduler** (tâches CPU avec un intervalle de refroidissement `n` entre tâches identiques, minimiser le temps total) : la tâche la plus fréquente dicte le cadre. Avec `maxFreq` et `countOfMax` tâches ayant cette fréquence, `réponse = max(tasks.length, (maxFreq-1)*(n+1) + countOfMax)`. Les créneaux libres sont remplis par d'autres tâches. Pour un « ordonnancement par priorité », utiliser une `PriorityQueue` ordonnée par priorité (puis ordre d'arrivée) et retirer la prochaine tâche à exécuter.

#### R17. Implémenter un cache LFU. {#lfu-cache-implementation}
**Réponse :** LFU évince la clé **la moins fréquemment utilisée** (égalités départagées par la moins récemment utilisée). Conception en O(1) : `Map<K, Node>` pour les valeurs, `Map<K, Integer>` pour la fréquence, et `Map<Integer, LinkedHashSet<K>>` associant chaque fréquence aux clés par ordre de récence, plus un pointeur `minFreq`.

```java
class LFUCache {
    private final int cap; private int minFreq;
    private final Map<Integer, Integer> val = new HashMap<>(), freq = new HashMap<>();
    private final Map<Integer, LinkedHashSet<Integer>> buckets = new HashMap<>();
    LFUCache(int cap) { this.cap = cap; }

    int get(int k) {
        if (!val.containsKey(k)) return -1;
        touch(k);
        return val.get(k);
    }
    void put(int k, int v) {
        if (cap == 0) return;
        if (val.containsKey(k)) { val.put(k, v); touch(k); return; }
        if (val.size() == cap) {                          // évince le LFU, le plus ancien parmi les égalités
            int old = buckets.get(minFreq).iterator().next();
            buckets.get(minFreq).remove(old); val.remove(old); freq.remove(old);
        }
        val.put(k, v); freq.put(k, 1); minFreq = 1;
        buckets.computeIfAbsent(1, f -> new LinkedHashSet<>()).add(k);
    }
    private void touch(int k) {
        int f = freq.get(k);
        buckets.get(f).remove(k);
        if (buckets.get(f).isEmpty() && f == minFreq) minFreq++;
        freq.put(k, f + 1);
        buckets.computeIfAbsent(f + 1, x -> new LinkedHashSet<>()).add(k);
    }
}
```
Non thread-safe ; rendre les méthodes `synchronized` ou utiliser Caffeine (W-TinyLFU) en production.

#### R18. Afficher alternativement les nombres pairs et impairs avec deux threads, et implémenter Producteur-Consommateur avec `wait()`/`notify()`. {#alternate-odd-even-threads-producer-consumer-wait-notify}
**Réponse :** Les deux reposent sur un **moniteur partagé**, une **condition testée dans une boucle `while`** (protège des réveils parasites) et `notifyAll`. **Affichage impair/pair** :

```java
class OddEven {
    private int n = 1; private final int max = 10;
    synchronized void print(boolean odd) throws InterruptedException {
        while (n <= max) {
            if ((n % 2 == 1) != odd) wait();             // pas mon tour
            else { System.out.println(Thread.currentThread().getName() + " " + n++); notifyAll(); }
        }
        notifyAll();                                     // libère l'autre thread à la fin
    }
}
// new Thread(() -> o.print(true), "odd").start(); new Thread(() -> o.print(false), "even").start();
```
**Producteur-Consommateur** avec un tampon borné :

```java
class Buffer<T> {
    private final Queue<T> q = new ArrayDeque<>(); private final int cap;
    Buffer(int cap) { this.cap = cap; }
    synchronized void put(T t) throws InterruptedException {
        while (q.size() == cap) wait();                  // plein : le producteur attend
        q.add(t); notifyAll();
    }
    synchronized T take() throws InterruptedException {
        while (q.isEmpty()) wait();                      // vide : le consommateur attend
        T t = q.poll(); notifyAll(); return t;
    }
}
```
En vrai code, préférer `BlockingQueue` (`ArrayBlockingQueue`) qui fait exactement cela ; montrer qu'on connaît `wait/notify` en dessous. `wait` doit être appelé en détenant le moniteur et le libère pendant l'attente.

#### R19. Implémenter du rate limiting d'API en Java : au plus 5 requêtes par utilisateur et par minute. {#rate-limiting-five-requests-per-user-per-minute-java}
**Réponse :** Un **journal à fenêtre glissante** par utilisateur est exact et simple : garder une deque d'horodatages de requêtes, retirer ceux de plus de 60 s, autoriser s'il en reste moins de 5.

```java
class RateLimiter {
    private final int max; private final long windowMs;
    private final ConcurrentHashMap<String, Deque<Long>> hits = new ConcurrentHashMap<>();
    RateLimiter(int max, long windowMs) { this.max = max; this.windowMs = windowMs; }

    boolean allow(String user) {
        long now = System.currentTimeMillis();
        Deque<Long> q = hits.computeIfAbsent(user, k -> new ArrayDeque<>());
        synchronized (q) {                                // verrou par utilisateur, pas global
            while (!q.isEmpty() && now - q.peekFirst() >= windowMs) q.pollFirst();
            if (q.size() >= max) return false;            // -> répondre 429 + Retry-After
            q.addLast(now);
            return true;
        }
    }
}
```
Coûte O(max) mémoire par utilisateur. Alternatives : compteur à **fenêtre fixe** (peu coûteux mais autorise 2× de rafale à la frontière), **token bucket** (lisse, autorise les rafales, état en O(1)). En déploiement multi-instances, les compteurs doivent être partagés (Redis `INCR` + `EXPIRE`, ou script Lua) ou appliqués à la gateway. Évincer les utilisateurs inactifs pour éviter une map non bornée.

#### R20. Comment aborder les questions « prédire la sortie » sur les Collections, les chaînes et le multithreading ? {#predict-the-output-collections-strings-threads}
**Réponse :** Dérouler le code sur papier, pas à pas, et vérifier les pièges classiques : **String** : `==` vs `equals` (les littéraux sont internés, `new String` non ; `s1 + s2` à l'exécution crée un nouvel objet, les constantes de compilation sont internées), immutabilité (`s.concat("x")` sans affectation ne change rien), `intern()`. **Collections** : `Arrays.asList` est de taille fixe (`add` lève une exception), `List.of` est immuable (et refuse `null`), `remove(int)` vs `remove(Object)` sur `List<Integer>`, `ConcurrentModificationException` en modifiant pendant un for-each (utiliser `Iterator.remove`/`removeIf`), `HashSet` d'objets sans `hashCode`/`equals`, clés mutables dans une `HashMap`, `TreeSet` qui utilise le comparateur pour l'égalité, cache d'autoboxing des `Integer` (`127 == 127` vrai, `128 == 128` faux). **Threads** : `run()` vs `start()` (run s'exécute sur le thread appelant), entrelacements non déterministes (sans `join`, l'ordre d'affichage n'est pas défini : le dire), `volatile`/synchronisation manquants (visibilité, mises à jour perdues sur `count++`), `finally` + `return`, ordre d'initialisation statique. Énoncer la réponse et la *règle* sous-jacente, et signaler quand la sortie est non déterministe.

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
