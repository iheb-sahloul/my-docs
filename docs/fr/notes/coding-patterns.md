# Patterns de code & katas

Une référence pour les épreuves de live coding et les sessions de kata : comment **reconnaître** un pattern à partir
de l'énoncé, un **modèle** à adapter, et des **exemples résolus** en Java 21. La version questions-réponses
d'entretien (méthode, Big-O, pièges, scénarios) se trouve dans [Live coding](../interviews/coding.md).

## Méthode

### La boucle, en 60 secondes

1. **Clarifier** : taille de l'entrée, vide/null, doublons, négatifs, trié ?, sortie attendue pour un exemple.
2. **Exemples** : deux ou trois à la main, dont un cas limite.
3. **Force brute** : énoncez-la avec sa complexité. C'est votre filet de sécurité si vous bloquez.
4. **Pattern** : associez la forme du problème à un pattern ci-dessous, annoncez la meilleure complexité.
5. **Coder** : noms clairs, petites méthodes, parlez en tapant.
6. **Tester** : déroulez un exemple ligne par ligne, puis vide, un seul élément, tous égaux, extrêmes.
7. **Complexité** : temps et mémoire, puis ce que vous amélioreriez avec plus de temps.

La version complète est [Live coding Q1](../interviews/coding.md#approach-live-coding-exercise).

### Taille de l'entrée → complexité visée

Demandez **n** en premier : il indique quel pattern l'intervieweur attend.

| n | Cible | Patterns typiques |
|---|---|---|
| ≤ 10–12 | O(n!) / O(2ⁿ·n) | Backtracking sur permutations ou sous-ensembles |
| ≤ 20–25 | O(2ⁿ) | Sous-ensembles, DP sur bitmask |
| ≤ 500 | O(n³) | Triple boucle, DP sur intervalles |
| ≤ 5 000 | O(n²) | DP 2D, toutes les paires |
| ≤ 10⁶ | O(n log n) / O(n) | Tri + parcours, tas, hachage, deux pointeurs, fenêtre glissante |
| ≥ 10⁹ (plage de valeurs) | O(log n) | Recherche dichotomique, maths |

### Choisir le pattern

| L'énoncé dit… | Essayez |
|---|---|
| « trouver une paire / compter les occurrences / déjà vu / doublons » | [Hachage](#hashing) |
| « tableau trié », « paire de somme », « en place », « palindrome » | [Deux pointeurs](#two-pointers) |
| « sous-tableau / sous-chaîne contiguë », « plus long / plus court / au plus K » | [Fenêtre glissante](#sliding-window) |
| « sous-tableau de somme K » (avec négatifs) | [Sommes préfixes + hachage](#hashing) |
| « cycle dans une liste chaînée », « milieu de la liste » | [Pointeurs lent & rapide](#fast-slow-pointers) |
| « trié », « le plus petit X tel que… », « le plus grand X tel que… » | [Recherche dichotomique](#binary-search) |
| « parenthèses équilibrées », « prochain plus grand / plus petit », « annuler » | [Pile / pile monotone](#stack-monotonic-stack) |
| « intervalles », « réunions », « réservations », « chevauchement » | [Intervalles](#intervals) |
| « top K », « K plus proches », « K-ième plus grand », « fusionner K listes triées » | [Tas](#heap-top-k) |
| « grille », « îles », « plus court chemin (non pondéré) », « dépendances » | [BFS / DFS / tri topologique](#bfs-dfs-graphs-grids) |
| « toutes les combinaisons / permutations / sous-ensembles », « générer chaque… » | [Backtracking](#backtracking) |
| « nombre de façons », « coût min / max », « plus longue sous-séquence » | [Programmation dynamique](#dynamic-programming) |
| « nombre minimal d'étapes / d'intervalles », le choix local semble sûr | [Glouton](#greedy) |
| « inverser / fusionner / réordonner une liste » | [Listes chaînées](#linked-lists) |
| « arbre », « profondeur », « chemin », « ABR », « niveau par niveau » | [Arbres](#trees) |

## Patterns

### Hachage {#hashing}

**Reconnaissez-le quand** la force brute est « pour chaque élément, chercher un partenaire dans le reste », ou quand
il faut compter, dédoublonner ou regrouper.

**Modèle :**

```java
Map<Integer, Integer> seen = new HashMap<>();      // ce qu'on cherchera -> ce dont on a besoin en retour
for (int i = 0; i < a.length; i++) {
    Integer hit = seen.get(complementOf(a[i]));    // 1. chercher d'abord
    if (hit != null) { /* trouvé */ }
    seen.put(a[i], i);                              // 2. puis enregistrer (évite d'apparier un élément avec lui-même)
}
```

**Exemple résolu : regrouper les anagrammes.** `["eat","tea","tan","ate","nat","bat"]` → `[[eat,tea,ate],[tan,nat],[bat]]`.

```java
List<List<String>> groupAnagrams(String[] words) {
    Map<String, List<String>> groups = new HashMap<>();
    for (String w : words) {
        char[] k = w.toCharArray();
        Arrays.sort(k);                                         // clé canonique
        groups.computeIfAbsent(new String(k), x -> new ArrayList<>()).add(w);
    }
    return new ArrayList<>(groups.values());
}
// O(n · m log m) en temps, O(n · m) en mémoire (m = longueur d'un mot)
```

**Exemple résolu : sous-tableaux de somme K (sommes préfixes).** Compter les sous-tableaux contigus de somme `k` ;
les valeurs peuvent être négatives, donc une fenêtre glissante ne marche pas. `sum(i..j) = prefix[j] - prefix[i-1]`,
donc pour chaque préfixe on compte combien de préfixes précédents valent `prefix - k`.

```java
int subarraySum(int[] nums, int k) {
    Map<Integer, Integer> count = new HashMap<>();
    count.put(0, 1);                                  // préfixe vide : sous-tableaux qui commencent à l'indice 0
    int prefix = 0, result = 0;
    for (int x : nums) {
        prefix += x;
        result += count.getOrDefault(prefix - k, 0);
        count.merge(prefix, 1, Integer::sum);
    }
    return result;
}
// [1, 2, 3], k = 3 -> 2 ([1,2] et [3]). O(n) en temps, O(n) en mémoire
```

**Pièges :** oublier l'amorce `count.put(0, 1)` ; enregistrer avant de chercher (apparie un élément avec lui-même) ;
clés mutables (une clé `List` modifiée après insertion est perdue) ; débordement d'un préfixe `int` (utilisez `long`
pour les grandes sommes).

**Pour s'entraîner :** two sum, contains duplicate, longest consecutive sequence, valid anagram, first unique
character.

### Deux pointeurs {#two-pointers}

**Reconnaissez-le quand** l'entrée est **triée** (ou peut l'être), qu'on cherche une paire/un triplet, qu'on compare
les deux extrémités, ou qu'il faut travailler **en place**.

**Modèle (extrémités opposées) :**

```java
int lo = 0, hi = a.length - 1;
while (lo < hi) {
    if (good(a[lo], a[hi])) { /* enregistrer */ lo++; hi--; }
    else if (needBigger(a[lo], a[hi])) lo++;
    else hi--;
}
```

**Exemple résolu : paire de somme cible dans un tableau trié.**

```java
int[] pairSum(int[] sorted, int target) {
    int lo = 0, hi = sorted.length - 1;
    while (lo < hi) {
        int sum = sorted[lo] + sorted[hi];
        if (sum == target) return new int[] { lo, hi };
        if (sum < target) lo++; else hi--;
    }
    return new int[0];
}
// O(n) en temps, O(1) en mémoire ; chaque étape écarte un candidat qui ne peut faire partie d'aucune réponse
```

**Exemple résolu : supprimer les doublons en place (pointeurs dans le même sens).** Retourne la nouvelle longueur ;
`slow` marque la fin du préfixe dédoublonné.

```java
int removeDuplicates(int[] sorted) {
    if (sorted.length == 0) return 0;
    int slow = 0;
    for (int fast = 1; fast < sorted.length; fast++)
        if (sorted[fast] != sorted[slow]) sorted[++slow] = sorted[fast];
    return slow + 1;
}
// [1,1,2,3,3] -> 3, le tableau commence par [1,2,3]. O(n) en temps, O(1) en mémoire
```

**Exemple résolu : container with most water.** Déplacez le mur le plus bas : la surface est plafonnée par lui, le
garder ne peut jamais aider.

```java
int maxArea(int[] h) {
    int lo = 0, hi = h.length - 1, best = 0;
    while (lo < hi) {
        best = Math.max(best, Math.min(h[lo], h[hi]) * (hi - lo));
        if (h[lo] < h[hi]) lo++; else hi--;
    }
    return best;
}
```

**Pièges :** l'utiliser sur une entrée non triée sans la trier (et perdre les indices d'origine) ; `lo <= hi` vs
`lo < hi` ; sauter les doublons dans 3-sum (`while (lo < hi && a[lo] == a[lo + 1]) lo++`).

**Pour s'entraîner :** valid palindrome, 3-sum, sort colors (drapeau hollandais), squares of a sorted array, trapping
rain water.

### Fenêtre glissante {#sliding-window}

**Reconnaissez-la quand** la réponse est un sous-tableau ou une sous-chaîne **contigu(ë)**, avec des mots comme « plus
long », « plus court », « au plus K distincts », « de taille K », et que la condition est **monotone** (agrandir la
fenêtre ne peut que la rendre « plus » invalide).

**Modèle (taille variable) :**

```java
int left = 0, best = 0;
for (int right = 0; right < n; right++) {
    add(a[right]);                       // 1. agrandir
    while (!valid()) remove(a[left++]);  // 2. réduire jusqu'à redevenir valide
    best = Math.max(best, right - left + 1);  // 3. enregistrer
}
```

**Exemple résolu : taille fixe, somme max de K éléments consécutifs.**

```java
long maxSumOfK(int[] a, int k) {
    long window = 0;
    for (int i = 0; i < k; i++) window += a[i];
    long best = window;
    for (int i = k; i < a.length; i++) {
        window += a[i] - a[i - k];      // glisser : ajouter le nouveau, retirer le plus ancien
        best = Math.max(best, window);
    }
    return best;
}
// O(n) au lieu de O(n·k)
```

**Exemple résolu : plus longue sous-chaîne avec au plus K caractères distincts.**

```java
int longestKDistinct(String s, int k) {
    Map<Character, Integer> count = new HashMap<>();
    int left = 0, best = 0;
    for (int right = 0; right < s.length(); right++) {
        count.merge(s.charAt(right), 1, Integer::sum);
        while (count.size() > k) {
            char c = s.charAt(left++);
            if (count.merge(c, -1, Integer::sum) == 0) count.remove(c);
        }
        best = Math.max(best, right - left + 1);
    }
    return best;
}
// "eceba", k = 2 -> 3 ("ece"). O(n) : chaque caractère entre et sort une seule fois de la fenêtre
```

**Exemple résolu : plus petite fenêtre contenant tous les caractères de `t`.** Variante « plus courte » : on réduit
**tant que c'est valide** et on enregistre dans la boucle.

```java
String minWindow(String s, String t) {
    int[] need = new int[128];
    for (char c : t.toCharArray()) need[c]++;
    int missing = t.length(), left = 0, bestStart = 0, bestLen = Integer.MAX_VALUE;
    for (int right = 0; right < s.length(); right++) {
        if (need[s.charAt(right)]-- > 0) missing--;
        while (missing == 0) {
            if (right - left + 1 < bestLen) { bestLen = right - left + 1; bestStart = left; }
            if (++need[s.charAt(left++)] > 0) missing++;
        }
    }
    return bestLen == Integer.MAX_VALUE ? "" : s.substring(bestStart, bestStart + bestLen);
}
// "ADOBECODEBANC", "ABC" -> "BANC". O(|s| + |t|)
```

**Pièges :** les nombres négatifs cassent les fenêtres « somme ≤ K » (réduire ne fait plus baisser la somme : utilisez
les sommes préfixes) ; enregistrer le meilleur en dehors ou dans la boucle de réduction (plus long = après, plus
court = dedans).

**Pour s'entraîner :** longest substring without repeating characters, longest repeating character replacement,
permutation in string, max consecutive ones III, fruit into baskets.

### Pointeurs lent & rapide {#fast-slow-pointers}

**Reconnaissez-le quand** vous travaillez sur une liste chaînée (ou une fonction `next = f(x)`) et cherchez un cycle,
le milieu ou le K-ième depuis la fin, en mémoire O(1).

```java
// ListNode est défini dans la section Listes chaînées plus bas
boolean hasCycle(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) return true;   // fast gagne un pas par tour, il rattrape forcément slow dans le cycle
    }
    return false;
}

ListNode middle(ListNode head) {        // 1-2-3-4-5 -> 3 ; 1-2-3-4 -> 3 (second milieu)
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }
    return slow;
}
```

**Exemple résolu : happy number** (pas de liste, mais la même astuce de cycle sur `n -> somme des carrés des chiffres`).

```java
boolean isHappy(int n) {
    int slow = n, fast = next(n);
    while (fast != 1 && slow != fast) { slow = next(slow); fast = next(next(fast)); }
    return fast == 1;
}
int next(int n) { int s = 0; for (; n > 0; n /= 10) s += (n % 10) * (n % 10); return s; }
```

**Pièges :** tester `fast.next.next` sans tester `fast.next` ; un `HashSet<Node>` marche aussi mais coûte O(n) en
mémoire, dites-le.

**Pour s'entraîner :** linked list cycle II (début du cycle), remove N-th node from end, palindrome linked list, find
the duplicate number.

### Recherche dichotomique {#binary-search}

**Reconnaissez-la quand** l'entrée est triée, **ou** quand la réponse est un nombre dans une plage et qu'un prédicat
`ok(x)` est monotone (faux…faux vrai…vrai) : « capacité minimale », « plus petite vitesse », « jour le plus tôt ».

**Modèle (lower bound : premier indice où `ok` est vrai).** Un seul modèle, plus de devinettes sur les off-by-one :

```java
int lowerBound(int lo, int hi) {         // cherche dans [lo, hi) ; retourne hi si jamais vrai
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;    // pas de débordement de (lo + hi) / 2
        if (ok(mid)) hi = mid;           // mid peut être la réponse : on le garde
        else lo = mid + 1;               // mid ne l'est pas : on l'écarte
    }
    return lo;
}
```

**Exemple résolu : première position de `target` dans un tableau trié avec doublons.**

```java
int firstIndexOf(int[] a, int target) {
    int lo = 0, hi = a.length;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] >= target) hi = mid; else lo = mid + 1;
    }
    return lo < a.length && a[lo] == target ? lo : -1;
}
```

**Exemple résolu : dichotomie sur la réponse, expédier des colis en D jours.** La capacité est entre le colis le plus
lourd et le poids total ; « expédiable en D jours avec la capacité c » est monotone en `c`.

```java
int shipWithinDays(int[] weights, int days) {
    int lo = Arrays.stream(weights).max().orElseThrow();
    int hi = Arrays.stream(weights).sum() + 1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (daysNeeded(weights, mid) <= days) hi = mid; else lo = mid + 1;
    }
    return lo;
}

int daysNeeded(int[] weights, int capacity) {
    int days = 1, load = 0;
    for (int w : weights) {
        if (load + w > capacity) { days++; load = 0; }
        load += w;
    }
    return days;
}
// [1..10], 5 jours -> 15. O(n log(somme)) en temps, O(1) en mémoire
```

**Pièges :** débordement de `(lo + hi) / 2` ; boucle infinie avec `lo = mid` (sûr seulement avec un milieu haut) ; un
prédicat non monotone ; oublier de vérifier que l'indice retourné est dans les bornes et correspond vraiment.

**Pour s'entraîner :** search insert position, search in rotated sorted array, find minimum in rotated array, Koko
eating bananas, median of two sorted arrays (difficile).

### Pile / pile monotone {#stack-monotonic-stack}

**Reconnaissez-la quand** le dernier élément ouvert doit être fermé en premier (parenthèses, balises, annuler), ou
qu'il faut l'élément **suivant / précédent plus grand ou plus petit** pour chaque position.

**Exemple résolu : parenthèses équilibrées.**

```java
boolean isBalanced(String s) {
    Deque<Character> stack = new ArrayDeque<>();
    Map<Character, Character> open = Map.of(')', '(', ']', '[', '}', '{');
    for (char c : s.toCharArray()) {
        if (open.containsValue(c)) stack.push(c);
        else if (open.containsKey(c) && (stack.isEmpty() || stack.pop() != open.get(c))) return false;
    }
    return stack.isEmpty();
}
// "([]{})" -> true, "(]" -> false, "((" -> false
```

**Modèle (pile monotone : élément suivant plus grand).** On garde les **indices** des éléments qui attendent encore
leur réponse ; la pile reste décroissante.

```java
int[] nextGreater(int[] a) {
    int[] res = new int[a.length];
    Arrays.fill(res, -1);
    Deque<Integer> stack = new ArrayDeque<>();          // indices, valeurs décroissantes du bas vers le haut
    for (int i = 0; i < a.length; i++) {
        while (!stack.isEmpty() && a[stack.peek()] < a[i]) res[stack.pop()] = a[i];
        stack.push(i);
    }
    return res;
}
// [2, 1, 2, 4, 3] -> [4, 2, 4, -1, -1]. O(n) : chaque indice est empilé et dépilé une fois
```

**Exemple résolu : daily temperatures** (jours à attendre avant un jour plus chaud) : même boucle, stockez
`i - stack.pop()` au lieu de `a[i]`.

**Pièges :** utiliser `java.util.Stack` (synchronisé, historique : utilisez `ArrayDeque`) ; `ArrayDeque` refuse
`null` ; stocker les valeurs quand il faut des distances (stockez les indices).

**Pour s'entraîner :** min stack, evaluate reverse Polish notation, largest rectangle in histogram, simplify path,
decode string.

### Intervalles {#intervals}

**Reconnaissez-les quand** vous voyez des plages `[début, fin]` : réunions, réservations, créneaux. **Triez par
début** d'abord, presque toujours.

**Exemple résolu : fusionner les intervalles qui se chevauchent.**

```java
int[][] merge(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(iv -> iv[0]));
    List<int[]> out = new ArrayList<>();
    for (int[] iv : intervals) {
        if (out.isEmpty() || out.getLast()[1] < iv[0]) out.add(iv);       // trou : nouvel intervalle
        else out.getLast()[1] = Math.max(out.getLast()[1], iv[1]);        // chevauchement : prolonger
    }
    return out.toArray(int[][]::new);
}
// [[1,3],[2,6],[8,10],[15,18]] -> [[1,6],[8,10],[15,18]]. O(n log n)
```

**Exemple résolu : nombre minimal de salles de réunion.** Tri par début ; un tas-min contient les heures de fin des
salles occupées.

```java
int minRooms(int[][] meetings) {
    Arrays.sort(meetings, Comparator.comparingInt(m -> m[0]));
    PriorityQueue<Integer> ends = new PriorityQueue<>();
    for (int[] m : meetings) {
        if (!ends.isEmpty() && ends.peek() <= m[0]) ends.poll();   // réutiliser la salle qui se libère en premier
        ends.offer(m[1]);
    }
    return ends.size();
}
// [[0,30],[5,10],[15,20]] -> 2
```

**Test de chevauchement** de deux intervalles semi-ouverts `[a1, a2)` et `[b1, b2)` : `a1 < b2 && b1 < a2`.

**Pièges :** clarifiez **fermé ou semi-ouvert** (`[1,2]` touche-t-il `[2,3]` ?) ; le comparateur `a[0] - b[0]` déborde
(utilisez `Integer.compare` / `comparingInt`) ; modifier le tableau d'entrée alors que l'appelant en a encore besoin.

**Pour s'entraîner :** insert interval, non-overlapping intervals (glouton), interval list intersections, employee
free time, créneaux libres dans un agenda ([Live coding Q28](../interviews/coding.md#given-practitioner-working-hours-existing)).

### Tas / top K {#heap-top-k}

**Reconnaissez-le quand** il faut les K plus grands/petits/fréquents, le K-ième élément, fusionner K sources triées,
ou toujours « le prochain plus petit » dans un ensemble qui change.

**Règle :** pour les K **plus grands**, gardez un **tas-min de taille K** et évincez le plus petit. O(n log K), pas
O(n log n).

**Exemple résolu : top K des mots les plus fréquents**, égalités départagées par ordre alphabétique.

```java
List<String> topKFrequent(String[] words, int k) {
    Map<String, Integer> freq = new HashMap<>();
    for (String w : words) freq.merge(w, 1, Integer::sum);

    Comparator<String> worstFirst = Comparator.<String>comparingInt(freq::get)
            .thenComparing(Comparator.reverseOrder());          // moins fréquent, puis plus loin dans l'alphabet = pire
    PriorityQueue<String> heap = new PriorityQueue<>(worstFirst);
    for (String w : freq.keySet()) {
        heap.offer(w);
        if (heap.size() > k) heap.poll();                       // évincer le pire
    }
    List<String> out = new ArrayList<>();
    while (!heap.isEmpty()) out.add(heap.poll());
    return out.reversed();                                       // le meilleur en premier
}
```

**Exemple résolu : fusionner K listes triées.**

```java
List<Integer> mergeK(List<List<Integer>> lists) {
    // entrée du tas : {valeur, indice de liste, indice d'élément}
    PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(e -> e[0]));
    for (int i = 0; i < lists.size(); i++)
        if (!lists.get(i).isEmpty()) heap.offer(new int[] { lists.get(i).get(0), i, 0 });
    List<Integer> out = new ArrayList<>();
    while (!heap.isEmpty()) {
        int[] e = heap.poll();
        out.add(e[0]);
        int next = e[2] + 1;
        if (next < lists.get(e[1]).size()) heap.offer(new int[] { lists.get(e[1]).get(next), e[1], next });
    }
    return out;
}
// O(N log K) pour N éléments au total
```

**Pièges :** itérer sur une `PriorityQueue` ne donne **pas** l'ordre trié (seul `poll` le fait) ; un tas-max via
`a - b` inversé déborde (utilisez `Comparator.reverseOrder()`) ; l'alternative « tout trier » convient pour un petit
n, dites-le.

**Pour s'entraîner :** K-th largest element, K closest points to origin, find median from data stream (deux tas),
task scheduler, reorganize string.

### BFS / DFS sur graphes et grilles {#bfs-dfs-graphs-grids}

**Reconnaissez-les quand** vous voyez une grille, un réseau, des dépendances, « connecté », « atteignable », ou « plus
court chemin » avec des arêtes de même poids.

- **BFS** (file) : plus court chemin dans un graphe **non pondéré**, niveau par niveau.
- **DFS** (récursion ou pile) : composantes connexes, détection de cycle, exploration de tous les chemins.
- **Tri topologique** : un ordre qui respecte les dépendances.

**Modèle (BFS sur grille avec distance) :**

```java
static final int[][] DIRS = { {1, 0}, {-1, 0}, {0, 1}, {0, -1} };

int shortestPath(char[][] grid, int sr, int sc, int tr, int tc) {   // '#' = mur
    int rows = grid.length, cols = grid[0].length;
    int[][] dist = new int[rows][cols];
    for (int[] row : dist) Arrays.fill(row, -1);
    Deque<int[]> queue = new ArrayDeque<>();
    queue.offer(new int[] { sr, sc });
    dist[sr][sc] = 0;                                    // marquer visité à l'ajout dans la file, pas au retrait
    while (!queue.isEmpty()) {
        int[] cur = queue.poll();
        if (cur[0] == tr && cur[1] == tc) return dist[tr][tc];
        for (int[] d : DIRS) {
            int r = cur[0] + d[0], c = cur[1] + d[1];
            if (r < 0 || c < 0 || r >= rows || c >= cols || grid[r][c] == '#' || dist[r][c] != -1) continue;
            dist[r][c] = dist[cur[0]][cur[1]] + 1;
            queue.offer(new int[] { r, c });
        }
    }
    return -1;
}
// O(rows · cols) en temps et en mémoire
```

**Exemple résolu : nombre d'îles (remplissage par DFS).**

```java
int numIslands(char[][] grid) {
    int count = 0;
    for (int r = 0; r < grid.length; r++)
        for (int c = 0; c < grid[0].length; c++)
            if (grid[r][c] == '1') { count++; sink(grid, r, c); }
    return count;
}

void sink(char[][] g, int r, int c) {
    if (r < 0 || c < 0 || r >= g.length || c >= g[0].length || g[r][c] != '1') return;
    g[r][c] = '0';                                       // marquer visité en modifiant (dites-le ; copiez si interdit)
    sink(g, r + 1, c); sink(g, r - 1, c); sink(g, r, c + 1); sink(g, r, c - 1);
}
```

**Exemple résolu : course schedule (tri topologique, algorithme de Kahn).** Peut-on suivre tous les cours étant
donné des paires `[cours, prérequis]` ? Retourne un ordre, ou une liste vide s'il y a un cycle.

```java
List<Integer> courseOrder(int n, int[][] prereqs) {
    List<List<Integer>> next = new ArrayList<>();
    for (int i = 0; i < n; i++) next.add(new ArrayList<>());
    int[] indegree = new int[n];
    for (int[] p : prereqs) { next.get(p[1]).add(p[0]); indegree[p[0]]++; }

    Deque<Integer> ready = new ArrayDeque<>();
    for (int i = 0; i < n; i++) if (indegree[i] == 0) ready.offer(i);
    List<Integer> order = new ArrayList<>();
    while (!ready.isEmpty()) {
        int c = ready.poll();
        order.add(c);
        for (int d : next.get(c)) if (--indegree[d] == 0) ready.offer(d);
    }
    return order.size() == n ? order : List.of();      // des restes = un cycle
}
// O(V + E)
```

**Pièges :** marquer visité au retrait en BFS (les nœuds sont ajoutés plusieurs fois) ; une récursion profonde sur une
grille 1000×1000 fait déborder la pile (passez à une pile explicite ou au BFS) ; des arêtes pondérées demandent
Dijkstra, pas un BFS.

**Pour s'entraîner :** rotting oranges (BFS multi-source), clone graph, word ladder, Pacific Atlantic water flow,
network delay time (Dijkstra).

### Backtracking {#backtracking}

**Reconnaissez-le quand** il faut **générer toutes** les combinaisons, permutations, sous-ensembles ou placements
(N reines, sudoku), et que n est petit.

**Modèle : choisir → explorer → annuler.**

```java
void backtrack(State state, List<Result> out) {
    if (isComplete(state)) { out.add(snapshot(state)); return; }
    for (Choice c : choices(state)) {
        if (!allowed(state, c)) continue;   // élaguer tôt
        apply(state, c);                     // choisir
        backtrack(state, out);               // explorer
        undo(state, c);                      // annuler
    }
}
```

**Exemple résolu : sous-ensembles.**

```java
List<List<Integer>> subsets(int[] nums) {
    List<List<Integer>> out = new ArrayList<>();
    collect(nums, 0, new ArrayList<>(), out);
    return out;
}

void collect(int[] nums, int start, List<Integer> current, List<List<Integer>> out) {
    out.add(new ArrayList<>(current));                   // copie ! current continue de changer
    for (int i = start; i < nums.length; i++) {
        current.add(nums[i]);
        collect(nums, i + 1, current, out);
        current.removeLast();
    }
}
// [1,2,3] -> [], [1], [1,2], [1,2,3], [1,3], [2], [2,3], [3]. O(2ⁿ · n)
```

**Exemple résolu : permutations.**

```java
List<List<Integer>> permutations(int[] nums) {
    List<List<Integer>> out = new ArrayList<>();
    permute(nums, new boolean[nums.length], new ArrayList<>(), out);
    return out;
}

void permute(int[] nums, boolean[] used, List<Integer> current, List<List<Integer>> out) {
    if (current.size() == nums.length) { out.add(new ArrayList<>(current)); return; }
    for (int i = 0; i < nums.length; i++) {
        if (used[i]) continue;
        used[i] = true; current.add(nums[i]);
        permute(nums, used, current, out);
        used[i] = false; current.removeLast();
    }
}
// O(n! · n)
```

**Exemple résolu : combination sum** (réutilisation autorisée, candidats triés pour pouvoir s'arrêter tôt).

```java
void combine(int[] sortedCandidates, int start, int remaining, List<Integer> current, List<List<Integer>> out) {
    if (remaining == 0) { out.add(new ArrayList<>(current)); return; }
    for (int i = start; i < sortedCandidates.length && sortedCandidates[i] <= remaining; i++) {   // élagage
        current.add(sortedCandidates[i]);
        combine(sortedCandidates, i, remaining - sortedCandidates[i], current, out);                // i, pas i+1 : réutilisation
        current.removeLast();
    }
}
```

**Pièges :** ajouter `current` au lieu d'une copie (tous les résultats finissent identiques et vides) ; oublier
d'annuler ; doublons dans l'entrée (triez, puis `if (i > start && a[i] == a[i - 1]) continue`).

**Pour s'entraîner :** letter combinations of a phone number, generate parentheses, word search, N-queens, palindrome
partitioning.

### Programmation dynamique {#dynamic-programming}

**Reconnaissez-la quand** la question est « combien de façons », « coût minimal/maximal », « plus longue/courte
sous-séquence », « peut-on atteindre », et que la récursion brute **recalcule les mêmes sous-problèmes**.

**Recette :**

1. **État** : que signifie `dp[i]` (ou `dp[i][j]`), en une phrase ?
2. **Transition** : comment `dp[i]` se construit-il à partir d'états plus petits ?
3. **Cas de base** et emplacement de la **réponse**.
4. **Ordre** : remplir pour que les dépendances soient prêtes ; puis voir si seules la dernière ligne/les dernières
   valeurs servent (mémoire O(1) ou O(n)).

Commencez par la récursion + mémo (top-down) si c'est plus simple à expliquer, puis passez à une table (bottom-up).

**Exemple résolu : house robber (1D).** Somme max sans prendre deux maisons adjacentes.
`dp[i] = max(dp[i-1], dp[i-2] + a[i])`.

```java
int rob(int[] a) {
    int prev2 = 0, prev1 = 0;                   // dp[i-2], dp[i-1]
    for (int x : a) {
        int cur = Math.max(prev1, prev2 + x);   // sauter cette maison, ou la prendre
        prev2 = prev1;
        prev1 = cur;
    }
    return prev1;
}
// [2,7,9,3,1] -> 12 (2 + 9 + 1). O(n) en temps, O(1) en mémoire
```

**Exemple résolu : coin change** (nombre minimal de pièces, illimitées). `dp[montant] = 1 + min(dp[montant - pièce])`.

```java
int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, amount + 1);                // « infini » qui ne déborde pas sur + 1
    dp[0] = 0;
    for (int a = 1; a <= amount; a++)
        for (int c : coins)
            if (c <= a) dp[a] = Math.min(dp[a], dp[a - c] + 1);
    return dp[amount] > amount ? -1 : dp[amount];
}
// pièces [1,2,5], 11 -> 3 (5+5+1). O(montant · pièces)
```

**Exemple résolu : plus longue sous-séquence commune (2D).** `dp[i][j]` = LCS des `i` premiers caractères de `a` et
des `j` premiers de `b`.

```java
int lcs(String a, String b) {
    int[][] dp = new int[a.length() + 1][b.length() + 1];   // ligne/colonne 0 = préfixe vide
    for (int i = 1; i <= a.length(); i++)
        for (int j = 1; j <= b.length(); j++)
            dp[i][j] = a.charAt(i - 1) == b.charAt(j - 1)
                    ? dp[i - 1][j - 1] + 1
                    : Math.max(dp[i - 1][j], dp[i][j - 1]);
    return dp[a.length()][b.length()];
}
// "abcde", "ace" -> 3. O(n · m)
```

**Version top-down** de la même idée, quand la récursion est l'explication naturelle :

```java
Map<Integer, Long> memo = new HashMap<>();
long climbStairs(int n) {                       // façons de monter n marches par 1 ou 2
    if (n <= 1) return 1;
    Long cached = memo.get(n);
    if (cached != null) return cached;
    long ways = climbStairs(n - 1) + climbStairs(n - 2);
    memo.put(n, ways);
    return ways;
}
```

**Pièges :** `computeIfAbsent` avec une lambda récursive sur une `HashMap` lève `ConcurrentModificationException`
(utilisez get/put comme ci-dessus) ; un off-by-one entre « les i premiers éléments » et « l'indice i » ;
`Integer.MAX_VALUE + 1` comme infini déborde.

**Pour s'entraîner :** climbing stairs, maximum subarray (Kadane), longest increasing subsequence, word break, edit
distance, unique paths, sac à dos 0/1.

### Glouton {#greedy}

**Reconnaissez-le quand** on peut prouver qu'un choix local ne nuit jamais (« prendre l'intervalle qui finit en
premier », « aller le plus loin possible »). Si vous ne savez pas justifier pourquoi, c'est probablement de la DP.

**Exemple résolu : jump game.** Peut-on atteindre le dernier indice (chaque valeur = longueur de saut max) ?

```java
boolean canJump(int[] nums) {
    int reach = 0;
    for (int i = 0; i < nums.length; i++) {
        if (i > reach) return false;            // bloqué avant i
        reach = Math.max(reach, i + nums[i]);
    }
    return true;
}
// [2,3,1,1,4] -> true, [3,2,1,0,4] -> false. O(n)
```

**Exemple résolu : nombre max d'intervalles disjoints** (ordonnancement d'intervalles). Triez par **fin**, prenez
chaque intervalle qui commence après la fin du dernier retenu.

```java
int maxNonOverlapping(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(iv -> iv[1]));
    int count = 0, lastEnd = Integer.MIN_VALUE;
    for (int[] iv : intervals)
        if (iv[0] >= lastEnd) { count++; lastEnd = iv[1]; }
    return count;
}
// Finir en premier laisse le plus de place au reste : argument d'échange
```

**Exemple résolu : sous-tableau de somme max (Kadane).** Abandonnez la somme courante quand elle devient un fardeau.

```java
int maxSubArray(int[] a) {
    int best = a[0], cur = a[0];
    for (int i = 1; i < a.length; i++) {
        cur = Math.max(a[i], cur + a[i]);
        best = Math.max(best, cur);
    }
    return best;
}
// [-2,1,-3,4,-1,2,1,-5,4] -> 6 ([4,-1,2,1])
```

**Pièges :** trier par début au lieu de fin pour l'ordonnancement d'intervalles ; le rendu de monnaie n'est **pas**
glouton pour des pièces arbitraires (`[1,3,4]`, 6 → le glouton donne 4+1+1, l'optimum est 3+3).

**Pour s'entraîner :** best time to buy and sell stock, gas station, partition labels, assign cookies, minimum arrows
to burst balloons.

### Listes chaînées {#linked-lists}

**Reconnaissez-les quand** l'entrée est un `ListNode`. Dessinez les pointeurs ; la plupart des bugs sont un `next`
perdu.

```java
class ListNode { int val; ListNode next; ListNode(int v, ListNode n) { val = v; next = n; } }
```

**Exemple résolu : inverser une liste.** Trois pointeurs : `prev`, `cur`, `next`.

```java
ListNode reverse(ListNode head) {
    ListNode prev = null, cur = head;
    while (cur != null) {
        ListNode next = cur.next;   // sauvegarder avant d'écraser
        cur.next = prev;
        prev = cur;
        cur = next;
    }
    return prev;
}
// 1->2->3 -> 3->2->1. O(n) en temps, O(1) en mémoire
```

**Exemple résolu : fusionner deux listes triées (astuce du nœud factice).** Un nœud factice supprime le cas
particulier « le résultat est-il encore vide ? ».

```java
ListNode mergeSorted(ListNode a, ListNode b) {
    ListNode dummy = new ListNode(0, null), tail = dummy;
    while (a != null && b != null) {
        if (a.val <= b.val) { tail.next = a; a = a.next; }
        else { tail.next = b; b = b.next; }
        tail = tail.next;
    }
    tail.next = a != null ? a : b;
    return dummy.next;
}
```

**Exemple résolu : supprimer le N-ième nœud depuis la fin.** Avancez `fast` de N pas, puis avancez les deux.

```java
ListNode removeNthFromEnd(ListNode head, int n) {
    ListNode dummy = new ListNode(0, head), fast = dummy, slow = dummy;
    for (int i = 0; i <= n; i++) fast = fast.next;
    while (fast != null) { fast = fast.next; slow = slow.next; }
    slow.next = slow.next.next;
    return dummy.next;
}
```

**Pièges :** perdre la suite de la liste en écrasant `next` d'abord ; oublier que la tête peut changer (utilisez un
nœud factice) ; contrôles de null quand `n` dépasse la longueur.

**Pour s'entraîner :** reorder list, add two numbers, intersection of two lists, copy list with random pointer, cache
LRU ([Live coding Q24](../interviews/coding.md#implement-lru-cache-o-1)).

### Arbres {#trees}

**Reconnaissez-les quand** vous voyez un arbre binaire, un ABR, une profondeur, des chemins, des ancêtres. La plupart
des réponses sont un **DFS récursif** qui renvoie quelque chose de chaque sous-arbre, ou un **BFS** pour les
questions niveau par niveau.

```java
record TreeNode(int val, TreeNode left, TreeNode right) {}
```

**Modèle (post-ordre : combiner les réponses des enfants).**

```java
int maxDepth(TreeNode node) {
    if (node == null) return 0;                                   // cas de base
    return 1 + Math.max(maxDepth(node.left()), maxDepth(node.right()));
}
```

**Exemple résolu : valider un ABR.** Transmettez la plage autorisée vers le bas ; ne vérifier que les enfants directs
est le bug classique.

```java
boolean isValidBst(TreeNode node, long min, long max) {   // appeler avec Long.MIN_VALUE, Long.MAX_VALUE
    if (node == null) return true;
    if (node.val() <= min || node.val() >= max) return false;
    return isValidBst(node.left(), min, node.val()) && isValidBst(node.right(), node.val(), max);
}
```

**Exemple résolu : parcours par niveaux (BFS).**

```java
List<List<Integer>> levels(TreeNode root) {
    List<List<Integer>> out = new ArrayList<>();
    if (root == null) return out;
    Deque<TreeNode> queue = new ArrayDeque<>(List.of(root));
    while (!queue.isEmpty()) {
        List<Integer> level = new ArrayList<>();
        for (int size = queue.size(); size > 0; size--) {   // figer d'abord la taille du niveau
            TreeNode n = queue.poll();
            level.add(n.val());
            if (n.left() != null) queue.offer(n.left());
            if (n.right() != null) queue.offer(n.right());
        }
        out.add(level);
    }
    return out;
}
```

**Exemple résolu : diamètre (réponse ≠ valeur de retour).** La récursion renvoie la profondeur, mais met à jour un
meilleur global avec « profondeur gauche + profondeur droite » à chaque nœud.

```java
int best = 0;
int diameter(TreeNode root) { depth(root); return best; }
int depth(TreeNode n) {
    if (n == null) return 0;
    int l = depth(n.left()), r = depth(n.right());
    best = Math.max(best, l + r);
    return 1 + Math.max(l, r);
}
```

**Pièges :** valider un ABR avec des bornes `int` échoue sur des nœuds `Integer.MIN_VALUE` (utilisez `long` ou des
bornes nullables) ; profondeur de récursion sur un arbre dégénéré (en forme de liste) ; confondre pré/in/post-ordre
(le parcours infixe d'un ABR est trié).

**Pour s'entraîner :** invert binary tree, lowest common ancestor, path sum, serialize/deserialize, K-th smallest in
a BST.

## Katas classiques (TDD)

Un kata est noté sur le **processus**, pas seulement sur le résultat : petites étapes rouge → vert → refactor, noms
de tests qui se lisent comme une spécification, refactoring sous tests verts. Dites « prochain test le plus simple
qui échoue » à voix haute. JUnit 5 + AssertJ ci-dessous.

### FizzBuzz {#fizzbuzz}

**Règles :** de 1 à 100, afficher le nombre, mais « Fizz » pour les multiples de 3, « Buzz » pour 5, « FizzBuzz »
pour les deux.

**Séquence de tests :** `1 → "1"`, `2 → "2"`, `3 → "Fizz"`, `5 → "Buzz"`, `6 → "Fizz"`, `15 → "FizzBuzz"`.

```java
@ParameterizedTest
@CsvSource({ "1,1", "2,2", "3,Fizz", "5,Buzz", "6,Fizz", "10,Buzz", "15,FizzBuzz", "30,FizzBuzz" })
void says(int n, String expected) {
    assertThat(FizzBuzz.say(n)).isEqualTo(expected);
}

static String say(int n) {
    String s = (n % 3 == 0 ? "Fizz" : "") + (n % 5 == 0 ? "Buzz" : "");
    return s.isEmpty() ? String.valueOf(n) : s;
}
```

**Relance de l'intervieweur :** « ajoutez 7 → Whizz ». La version par concaténation s'étend en ajoutant une règle ;
une chaîne de `if/else` explose. Une `LinkedHashMap<Integer, String>` de règles est le refactoring suivant,
**seulement** une fois qu'une troisième règle existe.

### String Calculator {#string-calculator}

**Règles (Roy Osherove) :** `add("")` → 0, `"1"` → 1, `"1,2"` → 3, un nombre quelconque de valeurs, retours à la
ligne comme séparateurs (`"1\n2,3"`), délimiteur personnalisé `"//;\n1;2"`, les négatifs lèvent une exception qui les
liste tous, les nombres > 1000 sont ignorés.

**Séquence de tests :** un test par règle, dans cet ordre ; refactor après chaque vert.

```java
class StringCalculator {
    int add(String input) {
        if (input.isEmpty()) return 0;
        String delimiters = ",|\n";
        if (input.startsWith("//")) {
            int nl = input.indexOf('\n');
            delimiters = Pattern.quote(input.substring(2, nl));
            input = input.substring(nl + 1);
        }
        List<Integer> numbers = Arrays.stream(input.split(delimiters)).map(Integer::parseInt).toList();
        List<Integer> negatives = numbers.stream().filter(n -> n < 0).toList();
        if (!negatives.isEmpty()) throw new IllegalArgumentException("negatives not allowed: " + negatives);
        return numbers.stream().filter(n -> n <= 1000).mapToInt(Integer::intValue).sum();
    }
}

@Test void emptyIsZero()            { assertThat(calc.add("")).isZero(); }
@Test void sumsManyNumbers()        { assertThat(calc.add("1,2,3,4")).isEqualTo(10); }
@Test void newlineIsADelimiter()    { assertThat(calc.add("1\n2,3")).isEqualTo(6); }
@Test void customDelimiter()        { assertThat(calc.add("//;\n1;2")).isEqualTo(3); }
@Test void ignoresAbove1000()       { assertThat(calc.add("2,1001")).isEqualTo(2); }
@Test void listsAllNegatives() {
    assertThatThrownBy(() -> calc.add("1,-2,-3")).hasMessageContaining("[-2, -3]");
}
```

**Ce qui est observé :** `Pattern.quote` pour des délimiteurs comme `*` ou `.` (métacaractères regex) ; ne pas écrire
le code du délimiteur personnalisé avant que son test existe.

### Chiffres romains {#roman-numerals}

**Règles :** convertir 1..3999 en chiffres romains (1994 → « MCMXCIV »).

**Séquence de tests :** 1 → I, 2 → II, 4 → IV, 5 → V, 9 → IX, 10 → X, 40 → XL… L'astuce apparaît après IV et IX :
mettre les **paires soustractives dans la table** au lieu d'en faire des cas particuliers.

```java
private static final int[] VALUES = { 1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1 };
private static final String[] SYMBOLS = { "M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I" };

static String toRoman(int n) {
    if (n < 1 || n > 3999) throw new IllegalArgumentException("out of range: " + n);
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < VALUES.length; i++)
        for (; n >= VALUES[i]; n -= VALUES[i]) sb.append(SYMBOLS[i]);   // le glouton marche pour cette table
    return sb.toString();
}

static int fromRoman(String s) {
    Map<Character, Integer> v = Map.of('I', 1, 'V', 5, 'X', 10, 'L', 50, 'C', 100, 'D', 500, 'M', 1000);
    int total = 0;
    for (int i = 0; i < s.length(); i++) {
        int cur = v.get(s.charAt(i));
        boolean subtract = i + 1 < s.length() && cur < v.get(s.charAt(i + 1));   // IV, IX, XL…
        total += subtract ? -cur : cur;
    }
    return total;
}
```

**Test de propriété** à mentionner : `fromRoman(toRoman(n)) == n` pour tout n dans 1..3999.

### Bowling Game {#bowling-game}

**Règles (Uncle Bob) :** 10 frames ; un **spare** (10 quilles en deux lancers) vaut 10 + le lancer suivant ; un
**strike** (10 au premier lancer) vaut 10 + les deux lancers suivants ; la 10e frame donne des lancers bonus.

**Séquence de tests :** partie dans la rigole (tout à 0) → 0 ; que des 1 → 20 ; un spare ; un strike ; partie
parfaite (12 strikes) → 300.

```java
class BowlingGame {
    private final List<Integer> rolls = new ArrayList<>();

    void roll(int pins) { rolls.add(pins); }

    int score() {
        int score = 0, i = 0;                        // i = premier lancer de la frame courante
        for (int frame = 0; frame < 10; frame++) {
            if (rolls.get(i) == 10) {                // strike
                score += 10 + rolls.get(i + 1) + rolls.get(i + 2);
                i += 1;
            } else if (rolls.get(i) + rolls.get(i + 1) == 10) {   // spare
                score += 10 + rolls.get(i + 2);
                i += 2;
            } else {
                score += rolls.get(i) + rolls.get(i + 1);
                i += 2;
            }
        }
        return score;
    }
}

@Test void perfectGame() {
    for (int i = 0; i < 12; i++) game.roll(10);
    assertThat(game.score()).isEqualTo(300);
}
@Test void oneSpare() {
    game.roll(5); game.roll(5); game.roll(3);       // 10 + 3, puis 3
    for (int i = 0; i < 17; i++) game.roll(0);
    assertThat(game.score()).isEqualTo(16);
}
```

**Ce qui est observé :** itérer par **frame** et non par lancer (l'idée de conception clé) ; extraire
`isStrike(i)`, `isSpare(i)` une fois les tests verts ; un helper de test `rollMany(n, pins)`.

### Jeu de la vie {#game-of-life}

**Règles :** une cellule vivante avec 2 ou 3 voisines vivantes survit ; une cellule morte avec exactement 3 naît ;
tout le reste meurt ou reste mort.

**Séquence de tests :** la fonction de règle d'abord (pure, pilotée par table), puis la grille : un clignotant
oscille, un bloc reste immobile.

```java
static boolean nextState(boolean alive, int liveNeighbours) {
    return liveNeighbours == 3 || (alive && liveNeighbours == 2);
}

// Plateau infini : on ne stocke que les cellules vivantes, la grille n'a jamais besoin d'être redimensionnée
record Cell(int x, int y) {
    Stream<Cell> neighbours() {
        return IntStream.rangeClosed(-1, 1).boxed()
                .flatMap(dx -> IntStream.rangeClosed(-1, 1).mapToObj(dy -> new Cell(x + dx, y + dy)))
                .filter(c -> !c.equals(this));
    }
}

static Set<Cell> tick(Set<Cell> alive) {
    Map<Cell, Long> counts = alive.stream()
            .flatMap(Cell::neighbours)
            .collect(Collectors.groupingBy(c -> c, Collectors.counting()));
    return counts.entrySet().stream()
            .filter(e -> nextState(alive.contains(e.getKey()), e.getValue().intValue()))
            .map(Map.Entry::getKey)
            .collect(Collectors.toSet());
}

@Test void blinkerOscillates() {
    Set<Cell> horizontal = Set.of(new Cell(0, 1), new Cell(1, 1), new Cell(2, 1));
    Set<Cell> vertical = Set.of(new Cell(1, 0), new Cell(1, 1), new Cell(1, 2));
    assertThat(tick(horizontal)).isEqualTo(vertical);
    assertThat(tick(vertical)).isEqualTo(horizontal);
}
```

**Ce qui est observé :** ne jamais modifier le plateau en place (la génération suivante se calcule uniquement à
partir de la courante) ; séparer la règle du plateau ; le modèle creux `Set<Cell>` comme sujet de discussion de
conception.

### Gilded Rose (kata de refactoring) {#gilded-rose}

**Contexte :** vous recevez un `updateQuality()` legacy plein de `if` imbriqués et devez ajouter les objets
« Conjured » (qui se dégradent deux fois plus vite) sans casser le comportement existant. C'est un exercice de
**refactoring**, pas d'algorithmique.

**Étapes :**

1. **Tests de caractérisation d'abord** : figer le comportement actuel. Le plus rapide : un test golden master qui
   fait tourner chaque type d'objet sur ~30 jours et compare la sortie imprimée à un instantané stocké (approval
   testing).
2. **Refactorer à petits pas** sous tests verts : extraire des méthodes par objet, inverser les conditions, supprimer
   la duplication.
3. Introduire le polymorphisme **une fois les branches isolées** : un updater par type d'objet.
4. **Ensuite** ajouter Conjured, test d'abord.

```java
interface Updater { void update(Item item); }

static Updater updaterFor(Item item) {
    return switch (item.name) {
        case "Aged Brie" -> i -> { i.sellIn--; i.quality = Math.min(50, i.quality + (i.sellIn < 0 ? 2 : 1)); };
        case "Sulfuras, Hand of Ragnaros" -> i -> { };                        // ne change jamais
        case "Backstage passes to a TAFKAL80ETC concert" -> i -> {
            i.sellIn--;
            i.quality = i.sellIn < 0 ? 0
                    : Math.min(50, i.quality + (i.sellIn < 5 ? 3 : i.sellIn < 10 ? 2 : 1));
        };
        default -> degrading(item.name.startsWith("Conjured") ? 2 : 1);
    };
}

static Updater degrading(int rate) {
    return i -> { i.sellIn--; i.quality = Math.max(0, i.quality - rate * (i.sellIn < 0 ? 2 : 1)); };
}
```

**Ce qui est observé :** écrivez-vous les tests **avant** de toucher au code ; committez-vous à chaque étape verte ;
laissez-vous la classe `Item` tranquille (le kata interdit de la modifier, lisez les contraintes).

### Compte bancaire {#bank-account}

**Règles :** `deposit(amount)`, `withdraw(amount)`, `printStatement()` avec date, montant et solde courant, le plus
récent en premier. Le kata porte sur la **conception** : value objects, horloge injectée, séparation du stockage et
du formatage.

```java
record Transaction(LocalDate date, BigDecimal amount) {}

class Account {
    private final List<Transaction> transactions = new ArrayList<>();
    private final Clock clock;                       // injectée : les tests contrôlent « aujourd'hui »

    Account(Clock clock) { this.clock = clock; }

    void deposit(BigDecimal amount)  { record(requirePositive(amount)); }
    void withdraw(BigDecimal amount) {
        if (balance().compareTo(amount) < 0) throw new IllegalStateException("insufficient funds");
        record(requirePositive(amount).negate());
    }

    BigDecimal balance() {
        return transactions.stream().map(Transaction::amount).reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    String statement() {
        List<String> lines = new ArrayList<>();
        BigDecimal running = BigDecimal.ZERO;
        for (Transaction t : transactions) {
            running = running.add(t.amount());
            lines.add("%s | %s | %s".formatted(t.date(), t.amount(), running));
        }
        return "date | amount | balance\n" + String.join("\n", lines.reversed());
    }

    private void record(BigDecimal amount) { transactions.add(new Transaction(LocalDate.now(clock), amount)); }

    private static BigDecimal requirePositive(BigDecimal a) {
        if (a.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
        return a;
    }
}

@Test void statementIsNewestFirstWithRunningBalance() {
    Account account = new Account(Clock.fixed(Instant.parse("2026-01-10T10:00:00Z"), ZoneOffset.UTC));
    account.deposit(new BigDecimal("1000"));
    account.withdraw(new BigDecimal("400"));
    assertThat(account.statement()).isEqualTo("""
            date | amount | balance
            2026-01-10 | -400 | 600
            2026-01-10 | 1000 | 1000""");
}
```

**Ce qui est observé :** `BigDecimal` (jamais `double`) pour l'argent ; une `Clock` injectée au lieu de
`LocalDate.now()` ; la validation des montants négatifs et du découvert ; un test d'acceptation outside-in d'abord,
puis les tests unitaires.

### Autres katas à connaître

| Kata | Ce qu'il entraîne |
|---|---|
| Prime factors | De toutes petites étapes TDD où l'algorithme « émerge » des tests |
| Word wrap | Choisir le test suivant pour que le code ne fasse pas un bond géant |
| Mars Rover | Commandes, machine à états, value objects (`Position`, `Direction`) |
| Tennis (refactoring) | Transformer une fonction de score emmêlée en code lisible |
| Parking / distributeur automatique | Conception objet sous des exigences qui évoluent |
| Mastermind | Compter les bien placés et mal placés (hachage) |
| Cache LRU | `LinkedHashMap(accessOrder=true)` + `removeEldestEntry`, ou map + liste doublement chaînée |

## Boîte à outils Java pour le live coding

| Besoin | Utiliser | Notes |
|---|---|---|
| Recherche, comptage, dédoublonnage | `HashMap`, `HashSet` | `merge(k, 1, Integer::sum)`, `getOrDefault`, `computeIfAbsent` |
| Pile et file | `ArrayDeque` | `push/pop/peek` (pile), `offer/poll/peek` (file) ; pas de `null` |
| Tas min/max | `PriorityQueue` | `new PriorityQueue<>(Comparator.reverseOrder())` pour un max |
| Clés triées, floor/ceiling | `TreeMap`, `TreeSet` | `floorKey`, `ceilingKey`, `headMap`, `pollFirst` |
| Ordre d'insertion / LRU | `LinkedHashMap` | `accessOrder = true` + `removeEldestEntry` |
| Comptage sur un petit alphabet | `int[26]`, `int[128]` | `count[c - 'a']++`, plus rapide qu'une map |
| Construction de chaînes | `StringBuilder` | `reverse()`, `setLength(0)`, `deleteCharAt` |
| Tri | `Arrays.sort`, `List.sort` | Comparateurs : `comparingInt(...).thenComparing(...)` |
| Collections séquencées Java 21 | `getFirst()`, `getLast()`, `removeLast()`, `reversed()` | Sur `List`, `Deque`, `LinkedHashMap` |
| Grands nombres | `long`, `Math.addExact`, `BigInteger` | Le débordement est une relance classique |

Fonctionnement interne et complexités des collections : [Java Q14](../interviews/java-core-jvm.md#arraylist-linkedlist-hashmap-treemap-linkedhashmap).

**Pièges :** `Integer == Integer` au-delà de 127 ; les comparateurs `(a, b) -> a - b` débordent ; `Arrays.asList` est
de taille fixe ; `List.of` est immuable et refuse `null` ; `char + int` donne un `int` ; `s.split(".")` exige
`"\\."` ; profondeur de récursion d'environ 10⁴ frames par défaut.

## Plan d'entraînement

**Format :** 25 minutes par problème, à voix haute, chrono lancé. Bloqué après 10 minutes : écrivez la force brute et
passez à la suite ; puis relisez le pattern ci-dessus et refaites le problème le lendemain.

| Semaine | Patterns | Problèmes |
|---|---|---|
| 1 | Hachage, deux pointeurs, fenêtre glissante | Two sum, group anagrams, 3-sum, longest substring without repeats, min window |
| 2 | Dichotomie, pile, intervalles | Search rotated array, ship within D days, valid brackets, daily temperatures, merge intervals |
| 3 | Tas, BFS/DFS, tri topologique | Top K frequent, merge K lists, islands, rotting oranges, course schedule |
| 4 | Backtracking, DP, glouton | Subsets, combination sum, coin change, LCS, house robber, jump game |
| Katas | Un par session, en TDD, un commit à chaque vert | FizzBuzz → String Calculator → Romains → Bowling → Jeu de la vie → Gilded Rose → Compte bancaire |

**Avant l'entretien :** refaites de mémoire un problème par pattern, et un kata de bout en bout avec ses tests.
