# Bonnes pratiques React & TypeScript



## 🔷 TypeScript

### Activez le mode `strict`
Mettez `"strict": true` dans `tsconfig.json`, et ajoutez `noUncheckedIndexedAccess` si possible.

**Pourquoi c'est une bonne pratique :** sans `strict`, `null` et `undefined` sont acceptés partout et les
paramètres non typés deviennent silencieusement `any`, donc le compilateur rate exactement les bugs pour lesquels
vous utilisez TypeScript (« cannot read properties of undefined »). `noUncheckedIndexedAccess` type `arr[i]` et
`record[key]` comme possiblement `undefined`, ce qu'ils sont. L'activer tard est pénible, donc commencez avec.

✅ `{ "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true } }`

### Utilisez `unknown`, pas `any`
Typez les valeurs que vous ne connaissez pas encore (réponses d'API, `JSON.parse`, erreurs de `catch`) en
`unknown`, et affinez leur type avant de les utiliser.

**Pourquoi c'est une bonne pratique :** `any` désactive la vérification de types, et il se propage : tout ce qui
dérive d'un `any` est aussi `any`. `unknown` accepte toutes les valeurs mais ne vous laisse rien en faire tant que
vous n'avez pas vérifié leur type, donc le compilateur impose la validation. Pour les données externes, validez
avec une bibliothèque de schémas (zod, valibot) qui vous donne le type et la vérification à l'exécution en une
seule fois.

```ts
// ⛔ aucune erreur jusqu'au plantage à l'exécution
const user: any = await res.json();
user.profile.name.toUpperCase();

// ✅ validé à la frontière
const User = z.object({ name: z.string() });
const user = User.parse(await res.json());
```

### Modélisez l'état avec des unions discriminées
Représentez les états mutuellement exclusifs par une union avec un champ `status` (ou `kind`), pas par plusieurs
booléens optionnels.

**Pourquoi c'est une bonne pratique :** `{ isLoading: boolean; error?: Error; data?: User }` autorise des
combinaisons impossibles : en chargement *et* en erreur, ou ni en chargement ni avec des données. Chaque composant
doit deviner lequel l'emporte. Une union discriminée rend les états invalides impossibles à représenter, et
TypeScript affine le type dans chaque branche : `data` n'existe que quand `status === 'success'`.

```ts
// ⛔ 8 combinaisons, 3 valides
type State = { isLoading: boolean; error?: Error; data?: User };

// ✅
type State =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: User };
```

### Utilisez `satisfies` et `as const` plutôt que `as`
Vérifiez une valeur par rapport à un type avec `satisfies`, et figez les valeurs littérales avec `as const`.
Évitez les casts `as`.

**Pourquoi c'est une bonne pratique :** `value as User` dit au compilateur de vous faire confiance, même quand il
manque des champs : l'erreur est repoussée à l'exécution. `satisfies` vérifie la valeur par rapport au type mais
garde son type inféré, plus précis. `as const` garde les types littéraux (`'admin'` au lieu de `string`) et rend
l'objet readonly, ce qui permet de dériver des types union à partir d'une seule source de vérité.

```ts
// ⛔ compile alors que `path` manque
const route = { name: 'home' } as Route;

// ✅
const ROLES = ['admin', 'editor', 'viewer'] as const;
type Role = (typeof ROLES)[number]; // 'admin' | 'editor' | 'viewer'
const config = { port: 3000 } satisfies Config;
```

## ⚛️ État & rendu

### Dérivez les valeurs au lieu de les synchroniser avec `useEffect`
Si une valeur peut être calculée à partir des props ou de l'état, calculez-la pendant le rendu. Ne la stockez pas
dans un autre état mis à jour dans un effet.

**Pourquoi c'est une bonne pratique :** synchroniser avec un effet fait deux rendus (un avec la valeur périmée,
puis un autre après l'effet), et les deux états peuvent se désynchroniser quand un chemin de mise à jour est
oublié. Une valeur calculée pendant le rendu est toujours correcte. Si le calcul est vraiment coûteux,
enveloppez-le dans `useMemo`, toujours sans état supplémentaire.

```tsx
// ⛔ rendu supplémentaire, risque de divergence
const [fullName, setFullName] = useState('');
useEffect(() => setFullName(`${first} ${last}`), [first, last]);

// ✅
const fullName = `${first} ${last}`;
```

### Ne mutez jamais l'état
Créez toujours un nouvel objet ou un nouveau tableau lors d'une mise à jour de l'état.

**Pourquoi c'est une bonne pratique :** React compare l'état par référence. Si vous faites `push` dans le tableau
existant puis appelez `setItems(items)`, la référence n'a pas changé, donc React saute le re-rendu et l'interface
affiche des données périmées. Les enfants mémoïsés et les effets qui dépendent de la valeur ratent aussi le
changement. Utilisez le spread, `map`, `filter`, ou `toSorted` / `toSpliced`, qui renvoient de nouveaux tableaux.

```tsx
// ⛔ même référence, pas de re-rendu
items.push(newItem);
setItems(items);

// ✅
setItems(prev => [...prev, newItem]);
```

### Utilisez des `key` stables et uniques dans les listes
Utilisez un id issu des données comme `key`, pas l'index du tableau.

**Pourquoi c'est une bonne pratique :** React utilise la key pour associer les éléments d'un rendu à l'autre. Avec
l'index, supprimer ou réordonner un élément décale les keys, donc React réutilise la mauvaise instance de
composant : les valeurs saisies, le focus et l'état local sautent sur la mauvaise ligne. Un id stable garde chaque
composant attaché à son élément. L'index n'est sûr que pour des listes statiques qui ne changent jamais d'ordre.

⛔ `items.map((item, i) => <Row key={i} item={item} />)`

✅ `items.map(item => <Row key={item.id} item={item} />)`

### Déclarez toutes les dépendances des effets et faites le nettoyage
Listez tout ce que l'effet utilise dans le tableau de dépendances (laissez la règle de lint
`react-hooks/exhaustive-deps` s'en charger), et renvoyez une fonction de nettoyage pour les abonnements, timers et
requêtes.

**Pourquoi c'est une bonne pratique :** une dépendance manquante fait que l'effet continue d'utiliser la valeur du
premier rendu (une closure périmée) : il charge l'ancien id ou envoie l'ancien filtre. Sans nettoyage, les timers
et les listeners s'accumulent à chaque re-rendu ou remontage, et une réponse lente peut arriver après une plus
récente et l'écraser. En développement, le Strict Mode de React monte les composants deux fois pour révéler les
nettoyages manquants.

```tsx
// ✅ ignorer les réponses périmées
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/users/${id}`, { signal: controller.signal }).then(/* ... */);
  return () => controller.abort();
}, [id]);
```

### Utilisez une bibliothèque de data fetching pour l'état serveur
Chargez les données serveur avec TanStack Query (ou SWR, ou les loaders de votre framework) plutôt qu'avec
`useState` + `useEffect`.

**Pourquoi c'est une bonne pratique :** le chargement écrit à la main dans des effets doit gérer les états de
chargement et d'erreur, les race conditions, le cache, la déduplication, les retries et le rechargement après une
mutation, et chaque composant finit par le faire un peu différemment. Ces bibliothèques font tout ça, partagent le
cache entre composants, et gardent l'interface synchronisée avec le serveur. Gardez `useState` pour le vrai état
d'interface (une modale ouverte, un champ de formulaire).

```tsx
// ✅
const { data, isPending, error } = useQuery({
  queryKey: ['user', id],
  queryFn: () => fetchUser(id),
});
```

### Ne mémoïsez que quand vous avez mesuré un problème
N'enveloppez pas chaque valeur dans `useMemo` et chaque fonction dans `useCallback` par défaut.

**Pourquoi c'est une bonne pratique :** la mémoïsation n'est pas gratuite : elle coûte de la mémoire, une
comparaison des dépendances à chaque rendu, et de la lisibilité. Elle n'aide que quand le calcul est vraiment
coûteux, ou quand la valeur est passée à un composant `memo` ou utilisée comme dépendance d'un effet. Utilisez
d'abord le profiler des React DevTools pour trouver les rendus lents. Le React Compiler mémoïse automatiquement,
ce qui rend inutiles la plupart des cas manuels.

⛔ `` const label = useMemo(() => `Hello ${name}`, [name]); ``
✅ `` const label = `Hello ${name}`; ``

## 🧩 Composants

### Gardez des composants petits et extrayez des custom hooks
Un composant, une responsabilité. Déplacez la logique avec état (chargement, abonnements, gestion de formulaire)
dans des custom hooks.

**Pourquoi c'est une bonne pratique :** un composant de 500 lignes qui mélange chargement de données, règles
métier et balisage est difficile à lire, se re-rend en entier, et ne peut pas être testé par morceaux. Un custom
hook (`useCart()`) donne un nom à la logique, peut être réutilisé par plusieurs composants et testé seul. Les
composants de présentation qui ne prennent que des props sont faciles à réutiliser et à montrer dans Storybook.

⛔ une `CheckoutPage` avec 12 `useState` et 4 `useEffect`
✅ `const cart = useCart(); const payment = usePayment();` + `<CartSummary cart={cart} />`

### Typez les props explicitement et évitez le prop drilling
Déclarez un type `Props` pour chaque composant. Quand la même prop traverse 3 niveaux ou plus, utilisez la
composition (`children`) ou un context.

**Pourquoi c'est une bonne pratique :** des types de props explicites documentent l'API du composant et détectent
les mauvais usages à chaque appel. Faire passer une prop à travers des composants qui ne l'utilisent pas les
couple tous : la renommer touche chaque niveau. Passer des éléments déjà construits en `children` supprime souvent
le besoin d'un context. Gardez le context pour les valeurs vraiment globales (thème, utilisateur courant), car
chaque consommateur se re-rend quand il change.

```tsx
// ✅
type ButtonProps = { variant: 'primary' | 'secondary'; onClick: () => void; children: React.ReactNode };
function Button({ variant, onClick, children }: ButtonProps) { /* ... */ }
```

## ♿ Formulaires & accessibilité

### Utilisez du HTML sémantique
Utilisez `<button>` pour les actions, `<a href>` pour la navigation, `<label>` pour les champs, et des titres dans
l'ordre.

**Pourquoi c'est une bonne pratique :** une `<div onClick>` n'est pas atteignable au clavier, n'est pas annoncée
comme un bouton par les lecteurs d'écran, et ne réagit ni à Entrée ni à Espace. Il faudrait tout reconstruire à
la main avec `role`, `tabIndex` et des handlers clavier. Les éléments natifs l'offrent gratuitement. Un champ sans
`<label>` n'a pas de nom pour les technologies d'assistance, et cliquer sur le libellé ne donne plus le focus au
champ.

⛔ `<div onClick={save}>Save</div>`, `<input placeholder="Email" />`
✅ `<button type="button" onClick={save}>Save</button>`, `<label>Email <input type="email" /></label>`

### Validez les formulaires avec un schéma
Utilisez une bibliothèque de formulaires (React Hook Form) avec un schéma (zod) au lieu de vérifications ad hoc
dans des handlers `onChange`.

**Pourquoi c'est une bonne pratique :** une validation écrite à la main est dispersée et incohérente, et les
règles diffèrent souvent entre le client et le serveur. Un schéma déclare toutes les règles au même endroit, vous
donne le type TypeScript des valeurs du formulaire, et peut être partagé avec le backend. La validation côté
client ne sert qu'à l'expérience utilisateur : le serveur doit valider à nouveau, car n'importe quel client peut
la contourner.

```tsx
// ✅
const schema = z.object({ email: z.string().email(), age: z.number().int().min(18) });
type FormValues = z.infer<typeof schema>;
const form = useForm<FormValues>({ resolver: zodResolver(schema) });
```
