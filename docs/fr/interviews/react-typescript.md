# React & TypeScript

## 🟢 Fondamentaux

### Bases de React

#### Q1. Qu'est-ce que JSX, et vers quoi compile-t-il réellement ?
JSX est du sucre syntaxique qui permet d'écrire une syntaxe de type balisage dans JavaScript ;
`<div className="a">{text}</div>` compile (via Babel ou le compilateur TypeScript) en un simple
appel de fonction — historiquement `React.createElement('div', {className: 'a'}, text)`, ou avec le
nouveau JSX transform, un appel `jsx()` importé automatiquement — qui retourne un objet JavaScript
simple décrivant l'élément (type, props, enfants), et non un nœud DOM. Le reconciler de React
transforme ensuite cet arbre d'objets en véritables opérations DOM. Comprendre cela est important
car cela explique pourquoi JSX a des règles que la syntaxe JavaScript n'a pas (un nom de composant
doit commencer par une majuscule pour que le compilateur le traite comme une référence à une
variable/fonction plutôt que comme une chaîne littérale de balise HTML) et pourquoi le rendu
conditionnel n'est que de simples expressions JavaScript, et non une syntaxe de template spéciale.

#### Q2. Que sont les hooks, et quel problème ont-ils résolu par rapport aux composants classes ?
Les hooks (`useState`, `useEffect`, etc.) permettent à un composant fonction de détenir un état et
de déclencher des effets de bord sans être une classe — avant les hooks, la logique avec état
exigeait des composants classes avec `this.state`/`this.setState` et des méthodes de cycle de vie
(`componentDidMount`, `componentDidUpdate`, `componentWillUnmount`) dispersées dans des méthodes
séparées même lorsqu'elles implémentaient une seule préoccupation logique (s'abonner dans
`componentDidMount`, se désabonner dans `componentWillUnmount` — du code lié, éclaté dans la
classe). Les hooks permettent à cette même préoccupation de vivre au même endroit dans une seule
fonction et, surtout, d'extraire la logique avec état dans des custom hooks réutilisables — ce que
les classes ne pouvaient obtenir qu'avec des higher-order components ou des render props, qui
ajoutaient tous deux des couches d'enrobage dans l'arbre de composants ("wrapper hell").

#### Q3. Quelle est la différence entre props et state, et pourquoi les données circulent-elles uniquement "vers le bas" ?
Les props sont les entrées qu'un composant *reçoit* de son parent ; le state est une donnée qu'un
composant *possède* et qui peut changer au fil du temps. Un composant doit traiter ses props comme
étant en lecture seule — il n'assigne jamais `props.x` — alors qu'il met à jour son propre state
via le setter (`setX`), qui planifie un re-render. Les données circulent dans un seul sens, du
parent vers l'enfant, via les props : quand le state d'un parent change, celui-ci refait un rendu
et passe de nouvelles props vers le bas, et un enfant qui doit influencer le parent le fait en
appelant une *fonction passée en prop* (`onChange`, `onSelect`). Cela rend le flux de données
traçable — pour toute valeur à l'écran, on peut remonter l'arbre jusqu'au unique composant qui la
possède — et c'est la raison pour laquelle "lifting state up" (Q15) est la réponse standard quand
deux frères ont besoin de la même donnée : déplacer le state vers leur ancêtre commun le plus
proche et le passer vers le bas. Les erreurs classiques sont de muter en place un objet ou un
tableau reçu en prop (React voit la même référence, donc les enfants mémoïsés ne se mettent pas à
jour, Q12) et de dupliquer une prop dans le state (Q16) au lieu d'en dériver.

#### Q4. `useState` vs `useRef` — quand utiliser l'un ou l'autre ?
`useState` déclenche un re-render quand sa valeur change, et sa valeur est celle avec laquelle
React fait le rendu au passage suivant — à utiliser pour tout ce qui doit apparaître dans l'UI.
`useRef` fournit un conteneur mutable (`.current`) qui persiste entre les rendus *sans* déclencher
de re-render quand il change — à utiliser pour les valeurs que le composant doit mémoriser mais qui
ne doivent pas piloter le rendu : une référence à un nœud DOM, un ID de timer/interval à nettoyer
plus tard, ou une "valeur précédente" à comparer. Le piège : utiliser `useRef` pour quelque chose
qui devrait réellement être dans l'UI (la valeur change mais l'écran ne se met jamais à jour, car
aucun re-render n'a été déclenché), ou utiliser `useState` pour quelque chose qui n'en a pas besoin
(provoquant des re-renders inutiles pour une valeur dont le rendu ne dépend jamais réellement).

#### Q5. Quelle est la différence entre un input de formulaire contrôlé et non contrôlé ?
La valeur d'un input contrôlé est entièrement pilotée par le state React — `<input value={value}
onChange={e => setValue(e.target.value)} />` — React est l'unique source de vérité, et chaque
frappe fait un aller-retour via une mise à jour de state et un re-render. Un input non contrôlé
gère son propre état DOM interne, React ne lisant la valeur courante que lorsque nécessaire (via
une `ref`, typiquement à la soumission) plutôt qu'à chaque frappe. Les inputs contrôlés sont le
choix par défaut car ils permettent la validation en temps réel, le formatage conditionnel et le
maintien de l'UI synchronisée avec le state pendant la saisie ; les inputs non contrôlés évitent le
coût de re-render à chaque frappe, ce qui compte parfois pour un formulaire réellement grand/complexe
(voir S5).

#### Q6. Quand la logique relève-t-elle d'un gestionnaire d'événement et quand de `useEffect` ?
Demandez-vous *pourquoi* le code s'exécute. S'il s'exécute parce que **l'utilisateur a fait
quelque chose** — cliqué, tapé, soumis — il relève du gestionnaire d'événement : c'est le moment où
la cause est connue, il s'exécute exactement une fois par interaction, et il a accès à l'événement.
`useEffect` sert à **se synchroniser avec quelque chose d'extérieur à React parce que le composant
est à l'écran ou parce qu'une valeur rendue a changé** : ouvrir une souscription WebSocket, démarrer
un timer, récupérer les données qu'un écran doit afficher, installer un listener. L'erreur
fréquente est d'utiliser un effet comme une chaîne de callbacks — "quand `submitted` passe à true,
faire un POST du formulaire", ou "quand `items` change, mettre à jour `total`" — ce qui ajoute un
rendu supplémentaire, masque la vraie cause, et se déclenche à tort en développement car le Strict
Mode exécute les effets deux fois (S9). Règle pratique tirée du "You might not need an effect" de
la doc React : si la valeur peut être *calculée à partir des props et du state pendant le rendu*,
calculez-la (pas de state, pas d'effet) ; si c'est une réponse à une action utilisateur, faites-le
dans le gestionnaire ; seul ce qui doit rester synchronisé avec un système externe après le rendu
est un effet — et il a alors besoin d'un cleanup (Q10).

### TypeScript

#### Q7. TypeScript `interface` vs `type` — quelle est la différence pratique, et quand choisir l'un plutôt que l'autre ?
Les deux peuvent décrire la forme d'un objet, et pour ce cas courant ils sont largement
interchangeables. Les différences concrètes : `interface` supporte le declaration merging (déclarer
deux fois le même nom d'interface fusionne les membres — parfois utile pour étendre les types de
bibliothèques tierces) et se lit un peu plus naturellement pour étendre d'autres interfaces
(`interface B extends A`) ; `type` peut représenter des choses qu'une interface ne peut pas — unions
(`type Status = 'idle' | 'loading' | 'error'`), intersections, mapped types et conditional types.
La règle pratique sur laquelle la plupart des équipes s'accordent : `interface` pour les formes
publiques d'objets/props de composants destinées à être étendues, `type` pour les unions, les
compositions d'utility types et tout ce qui n'est pas une simple forme d'objet — la cohérence au
sein d'une codebase compte plus que la règle précise choisie.

## 🟡 Pièges seniors

### Hooks & effets

#### Q8. Quelles sont les Rules of Hooks, et pourquoi un hook ne peut-il pas être appelé conditionnellement ?
**Réponse :** Les hooks doivent être appelés dans le même ordre à chaque rendu, et uniquement au
niveau supérieur d'un composant fonction ou d'un custom hook — jamais dans une condition, une boucle
ou une fonction imbriquée. C'est parce que React ne suit pas les hooks par nom ; il les suit par
*ordre d'appel* au sein d'une instance de composant (une liste chaînée interne associée à chaque
rendu), de sorte que le `useState` du "troisième hook appelé" ne correspond au même morceau de state
d'un rendu à l'autre que si le troisième hook appelé est toujours le même. Envelopper un appel de
hook dans `if (condition) { useState(...) }` signifie que, selon les rendus, il est le troisième
hook ou n'est plus du tout le troisième — React n'a aucun moyen de savoir quel state appartient à
quel appel, et le décalage corrompt l'association du state pour chaque hook suivant le conditionnel,
pas seulement pour ce hook.

**Exemple :**
```jsx
function Profile({ showBio }) {
  if (showBio) {
    const [bio, setBio] = useState(''); // l'ordre d'appel des hooks dépend désormais d'une prop
  }
  const [name, setName] = useState(''); // tantôt le 1er hook, tantôt le 2e
  // ...
}
```

**Pourquoi c'est un piège :** le code s'exécute souvent sans plantage immédiat, surtout si
`showBio` ne change jamais réellement au cours d'une session donnée — la corruption dépend du moment
exact où la condition change entre les rendus, ce qui explique pourquoi c'est facile à introduire et
difficile à remarquer jusqu'à ce qu'un parcours d'interaction précis le déclenche en production.

#### Q9. Qu'est-ce qu'une stale closure dans `useEffect`, et en quoi le tableau de dépendances y est-il lié ?
**Réponse :** Chaque rendu crée une nouvelle closure sur les valeurs de props/state de ce rendu ;
une fonction d'effet capture les valeurs qui étaient dans la portée *au moment de la création de
cette instance d'effet*. Si le tableau de dépendances omet une valeur que l'effet lit, l'effet n'est
recréé qu'aux rendus où une dépendance *listée* change — donc aux autres rendus, il continue
d'exécuter la closure de sa dernière création, lisant cette valeur capturée périmée plutôt que la
valeur courante. La solution n'est pas simplement "ajouter mécaniquement chaque valeur au tableau" —
il faut comprendre que le tableau contrôle *quand l'effet se ré-exécute avec des valeurs fraîches*,
et que chaque valeur lue par le corps de l'effet doit généralement y figurer (ou que la logique doit
être restructurée pour ne plus en avoir besoin, par ex. en utilisant une mise à jour fonctionnelle
du state `setCount(c => c + 1)` plutôt que de lire `count` directement).

**Exemple :**
```jsx
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(count); // affiche toujours 0 — cette closure a été créée une seule fois, au mount
    }, 1000);
    return () => clearInterval(id);
  }, []); // `count` manquant — l'effet ne se ré-exécute jamais pour récupérer une closure fraîche

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

**Pourquoi c'est un piège :** "il suffit de faire taire l'avertissement `exhaustive-deps`, il est
bruyant" est l'instinct qui crée ce bug — la règle de lint signale un vrai décalage de valeur
capturée, et non un faux positif à supprimer, et la supprimer échange un avertissement visible
contre un bug invisible dépendant du timing.

#### Q10. Pourquoi `useEffect` a-t-il besoin d'une fonction de cleanup, et que se passe-t-il si on l'omet pour une souscription ?
**Réponse :** Un effet peut s'exécuter de nombreuses fois au cours de la vie d'un composant (une fois
par changement du tableau de dépendances) et le composant lui-même finira par être démonté — une
fonction de cleanup (la fonction retournée par un effet) s'exécute avant la ré-exécution de l'effet
*et* au démontage du composant, défaisant ce que l'effet avait mis en place. Omettre le cleanup pour
un `setInterval`, une souscription WebSocket ou un event listener signifie que chaque ré-exécution de
l'effet empile *un autre* interval/souscription/listener par-dessus les précédents (puisque rien n'a
jamais démonté l'ancien), et le démontage du composant le laisse tourner indéfiniment en arrière-plan,
tentant souvent de mettre à jour le state d'un composant qui n'existe plus (un avertissement React
classique, S3) et gaspillant des ressources pendant toute la durée de vie de la page.

**Exemple :**
```jsx
useEffect(() => {
  const id = setInterval(() => ping(), 5000);
  return () => clearInterval(id); // sans ceci, chaque ré-exécution/démontage empile un interval de plus
}, [ping]);
```

**Pourquoi c'est un piège :** supposer que "le composant est démonté, donc son effet s'est sûrement
arrêté aussi" — démonter un composant n'annule pas automatiquement les effets de bord créés par ses
effets ; seule la fonction de cleanup retournée le fait, et l'omettre laisse fuir silencieusement
timers/souscriptions aussi longtemps que ce qu'ils ont mis en place continue de tourner.

### Rendu & performance

#### Q11. Pourquoi React refait-il un rendu, et comment les keys affectent-elles la réconciliation d'une liste ?
**Réponse :** Un composant refait un rendu quand son propre state change, quand ses props changent,
ou quand son parent refait un rendu (par défaut, un re-render du parent se propage à chaque enfant,
que les props de cet enfant aient réellement changé ou non, sauf si l'enfant est mémoïsé — Q12). Le
reconciler de React compare (diff) les arbres d'éléments précédent et nouveau pour calculer
l'ensemble minimal d'opérations DOM réelles nécessaires. Pour une liste, `key` indique au reconciler
quel élément de la nouvelle liste correspond à quel élément de l'ancienne d'un rendu à l'autre —
sans key stable et unique (ou pire, en utilisant l'index du tableau comme key pour une liste qui
est réordonnée/insérée/supprimée), React peut mal identifier quel nœud DOM correspond à quel item
logique, faisant apparaître le state associé à un item de liste (la valeur saisie dans un input, le
`useState` interne d'un composant) attaché au mauvais item après un réordonnancement (S14).

**Exemple :**
```jsx
{items.map((item, index) => (
  <Row key={index} {...item} /> // index comme key — casse si les items sont réordonnés/insérés/supprimés
))}
// vs.
{items.map(item => (
  <Row key={item.id} {...item} /> // une identité stable survit correctement au réordonnancement
))}
```

**Pourquoi c'est un piège :** les keys basées sur l'index du tableau "fonctionnent" parfaitement pour
une liste statique en ajout seul, ce qui est exactement pourquoi le bug survit à la code review — il
n'apparaît que la première fois que la liste est réellement réordonnée ou qu'un item est supprimé
ailleurs qu'à la fin.

#### Q12. Quand `React.memo` aide-t-il réellement, et pourquoi ne fait-il parfois silencieusement rien ?
**Réponse :** `React.memo` enveloppe un composant pour qu'il saute le re-render si ses props sont
égales (comparaison shallow) à celles du rendu précédent — il aide pour un composant dont le rendu
est coûteux (ou dont le sous-arbre l'est) et qui reçoit les mêmes props lors de la plupart des
re-renders de son parent. Il ne fait silencieusement rien lorsqu'une prop est un nouvel objet,
tableau ou fonction créé inline à chaque rendu du parent (`<Child data={{ id: 1 }} />` ou
`<Child onClick={() => ...} />`) — une nouvelle référence à chaque fois signifie que la
vérification d'égalité shallow échoue toujours, donc `React.memo` compare deux objets différents
qui ont par hasard un contenu égal et (à juste titre, selon sa comparaison shallow par défaut)
décide qu'ils sont différents, refaisant le rendu à chaque fois quoi qu'il arrive. La solution est
de mémoïser ce qui est passé en prop avec `useMemo`/`useCallback` (Q13) à l'endroit où c'est créé,
et pas seulement d'envelopper l'enfant récepteur — ne mémoïser qu'un côté de cette relation ne sert
à rien.

**Exemple :**
```jsx
const Row = React.memo(function Row({ onSelect }) { /* ... */ });

function List({ items }) {
  return items.map(item => (
    <Row key={item.id} onSelect={() => select(item.id)} /> // nouvelle fonction à chaque rendu
  ));
}
// La comparaison shallow des props de React.memo voit une référence `onSelect` différente à chaque fois —
// il refait le rendu de chaque Row à chaque rendu de List, malgré la mémoïsation.
```

**Pourquoi c'est un piège :** envelopper l'enfant dans `React.memo` donne l'impression d'avoir "fait
le travail de performance", mais ne mémoïser qu'un côté de la relation parent/enfant ne sert à rien
si le parent continue de créer de nouvelles références de props — les deux côtés doivent coopérer
pour que la mémoïsation tienne.

#### Q13. Quel problème `useMemo` et `useCallback` résolvent-ils chacun, et quel est le mauvais usage courant ?
**Réponse :** `useMemo` mémoïse une *valeur* calculée, ne la recalculant que lorsque ses
dépendances changent — utile quand un calcul est réellement coûteux (filtrer/trier un grand
tableau) et se ré-exécuterait sinon à chaque rendu. `useCallback` mémoïse une *référence de
fonction* elle-même, de sorte que la même identité de fonction est retournée d'un rendu à l'autre
tant que ses dépendances ne changent pas — utile spécifiquement quand cette référence de fonction
est passée à un enfant mémoïsé (`React.memo`, Q12) ou utilisée comme dépendance d'un autre hook,
puisqu'une nouvelle référence de fonction à chaque rendu annulerait sinon cette mémoïsation. Le
mauvais usage courant : recourir à l'un ou à l'autre par réflexe sur chaque valeur ou callback "pour
la performance", alors que pour un calcul peu coûteux ou un composant sans enfants mémoïsés, le
surcoût de la mémoïsation (la comparaison elle-même, plus la mémoire pour conserver la valeur en
cache) peut coûter plus cher que le travail de rendu qu'elle devait économiser — profilez avant
d'optimiser, ne l'appliquez pas comme une habitude par défaut.

**Exemple :**
```jsx
// Mémoïsation réflexe qui n'aide pas : `items` est petit, le filtrage est peu coûteux.
const visible = useMemo(() => items.filter(i => i.active), [items]);
// La mécanique de useMemo (comparaison des dépendances, stockage du cache) peut coûter plus cher que
// de simplement ré-exécuter un filtre peu coûteux à chaque rendu — profilez avant d'y recourir par défaut.
```

**Pourquoi c'est un piège :** traiter `useMemo`/`useCallback` comme une habitude de performance par
défaut plutôt que comme un correctif ciblé pour un coût *mesuré* — sur-mémoïser ajoute un vrai
surcoût (la comparaison plus le cache) sans bénéfice pour des calculs peu coûteux ou des composants
sans enfants mémoïsés en aval.

#### Q14. Quel problème `startTransition` / le rendu concurrent résolvent-ils ?
**Réponse :** Sans cela, une mise à jour de state qui déclenche un re-render coûteux (filtrer une
grande liste pendant que l'utilisateur tape dans une barre de recherche) bloque le main thread du
navigateur jusqu'à la fin de ce rendu, y compris en bloquant la mise à jour de state pilotée par la
frappe (la mise à jour de la valeur affichée de l'input lui-même) qui l'a déclenché — l'input semble
laggy parce que le rendu de la partie coûteuse et le rendu du retour immédiat de l'input sont traités
avec la même urgence synchrone. `startTransition` permet de marquer une mise à jour de state comme
non urgente ("cela peut être interrompu et terminé un peu plus tard"), de sorte que React peut
prioriser la mise à jour urgente (l'input reflétant ce qui vient d'être tapé) et différer/interrompre
la coûteuse, gardant l'UI réactive à la saisie même pendant qu'un gros re-render rattrape son retard
en arrière-plan.

**Exemple :**
```jsx
function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  function onChange(e) {
    setQuery(e.target.value);                            // urgent — garder l'input réactif
    startTransition(() => {
      setResults(filterBigList(e.target.value));          // non urgent — peut être interrompu
    });
  }
}
```

**Pourquoi c'est un piège :** envelopper la mise à jour de state *de l'input lui-même* dans
`startTransition` plutôt que celle, coûteuse, qui en est dérivée va totalement à l'encontre du but —
la mise à jour de l'input doit rester dans la voie urgente ; seule la mise à jour coûteuse et non
critique doit être différée.

### Gestion d'état

#### Q15. Qu'est-ce que le "prop drilling", et comment choisir entre remonter le state (lifting) et le colocaliser ?
**Réponse :** Le prop drilling consiste à passer une valeur à travers plusieurs couches de composants
qui ne l'utilisent pas eux-mêmes, uniquement pour qu'un descendant profondément imbriqué la reçoive —
chaque composant intermédiaire ajoute une prop inutilisée juste pour la retransmettre. La décision de
placement du state : garder le state le plus près possible de l'endroit où il est utilisé
(colocation) par défaut — ne pas remonter le state vers un ancêtre commun "au cas où" quelque chose
d'autre en aurait besoin un jour. Ne remonter le state que lorsque deux composants frères ou plus ont
réellement besoin de partager et de rester synchronisés sur la même valeur. Quand le lifting
imposerait de traverser de nombreuses couches sans rapport, c'est le vrai signal pour recourir au
Context (pour des valeurs qui changent rarement et sont largement nécessaires, comme le thème/l'auth)
ou à une bibliothèque de state (pour un state partagé qui change fréquemment) — pas pour continuer à
faire du drilling manuel, ni pour recourir prématurément à un state global pour quelque chose que
seuls deux composants proches partagent réellement.

**Exemple :**
```jsx
function Page({ user }) {                 // n'utilise pas `user` lui-même...
  return <Layout user={user} />;
}
function Layout({ user }) {                // ...celui-ci non plus...
  return <Sidebar user={user} />;
}
function Sidebar({ user }) {               // ...seul celui-ci en a réellement besoin.
  return <span>{user.name}</span>;
}
```

**Pourquoi c'est un piège :** remonter le state par réflexe vers un ancêtre commun "au cas où"
quelque chose d'autre en aurait besoin un jour ajoute exactement ce coût de drilling pour un besoin
qui ne se matérialisera peut-être jamais — colocalisez d'abord, et ne remontez que lorsque deux
frères ont réellement besoin de partager la valeur maintenant.

#### Q16. Pourquoi copier une prop dans un state local via `useEffect` est-il considéré comme un anti-pattern ?
**Réponse :** Cela crée deux sources de vérité pour la même donnée et un vrai bug de synchronisation :
tout rendu intermédiaire où `props.value` change mais où l'effet n'a pas encore tourné (les effets
s'exécutent *après* le commit du rendu, pas pendant) affiche le `localValue` périmé ; pire, si
`localValue` est modifié indépendamment (par ex. des modifications locales avant une sauvegarde), un
changement de prop ultérieur écrase silencieusement ces modifications locales, ou une modification
locale est silencieusement écrasée par une mise à jour de prop retardée — et c'est tout un cycle de
rendu supplémentaire (rendu avec la valeur périmée, l'effet s'exécute, le state se met à jour,
re-render) pour quelque chose qui pourrait généralement être dérivé directement pendant le rendu
(`const displayValue = props.value`), sans aucun `useState`/`useEffect`. Quand le state local doit
réellement diverger d'une prop intentionnellement (un formulaire éditable initialisé depuis une
prop, pouvant être édité avant la sauvegarde), le pattern accepté est soit un composant entièrement
non contrôlé avec une prop `key` qui remonte le composant quand la valeur source change (réinitialisant
proprement le state local), plutôt qu'une synchronisation via effet.

**Exemple :**
```jsx
// anti-pattern
const [localValue, setLocalValue] = useState(props.value);
useEffect(() => { setLocalValue(props.value); }, [props.value]);
// Une mise à jour de prop qui arrive entre "rendu avec localValue périmé" et "l'effet s'exécute" est
// visible de l'utilisateur pendant une frame complète, et toute modification locale faite dans cette fenêtre est perdue.
```

**Pourquoi c'est un piège :** cela semble raisonnable — "garder le state local synchronisé avec la
prop" — mais introduit un cycle de rendu supplémentaire complet et un vrai risque d'écrasement ; la
vraie bonne solution (dériver la valeur directement pendant le rendu, ou remonter le composant via une
`key` liée à la source) n'a besoin d'aucun couple `useState`/`useEffect`, ce qui est l'instinct
opposé à celui vers lequel ce pattern pousse.

#### Q17. Quand `useReducer` convient-il mieux que `useState` ?
**Réponse :** `useReducer` justifie sa structure quand les mises à jour du state impliquent plusieurs
sous-valeurs liées qui changent ensemble (de sorte qu'une seule action dispatchée peut mettre à jour
plusieurs champs de façon atomique et cohérente, au lieu de plusieurs appels `setState` séparés qui
peuvent se désynchroniser si l'un est oublié), quand le prochain state dépend réellement d'une logique
complexe basée sur le state précédent et l'action (pas seulement "remplacer par cette nouvelle
valeur"), ou quand la même logique de transition d'état doit être déclenchée depuis de nombreux
endroits différents (la centraliser sous forme d'actions nommées dans une seule fonction reducer est
plus facile à raisonner, et à tester isolément, que la même logique dupliquée dans plusieurs
gestionnaires `onClick` appelant chacun plusieurs `setState`). Pour des morceaux de state simples et
indépendants, `useState` reste plus simple et plus direct — recourir à `useReducer` par réflexe pour
un simple toggle booléen est une cérémonie inutile.

**Exemple :**
```jsx
// Plusieurs appels setState qui peuvent se désynchroniser si un site d'appel en oublie un :
setLoading(true); setError(null); setData(null);

// Une seule action dispatchée les garde atomiques et cohérents par construction :
dispatch({ type: 'FETCH_START' });
```

**Pourquoi c'est un piège :** recourir à `useReducer` pour un seul booléen indépendant est une
cérémonie inutile — le vrai signal est "ces champs changent-ils ensemble comme une seule transition
logique", et non simplement "y a-t-il plus d'un morceau de state".

#### Q18. Quel est le piège de performance du Context React, et quand devient-il un vrai problème ?
**Réponse :** Chaque composant qui consomme un context via `useContext` refait un rendu à chaque fois
que la valeur de ce context change — sans moyen intégré de ne souscrire qu'à une partie de la valeur,
contrairement à une bibliothèque de gestion d'état à granularité fine. Pour un context contenant une
grande valeur qui change fréquemment (surtout un objet recréé à chaque rendu du provider, comme
`{ user, theme, settings }` passé inline en `value={{ user, theme, settings }}` — une nouvelle
identité d'objet à chaque rendu même si les données réelles n'ont pas changé) consommée par de
nombreux composants dans l'arbre, cela peut déclencher une tempête de re-renders sur de larges
portions de l'UI pour un seul changement de state, possiblement sans rapport. Mitigations : découper
le context en providers plus petits et plus ciblés pour qu'un composant ne souscrive qu'à ce dont il a
réellement besoin, mémoïser l'objet valeur du context lui-même (`useMemo`) pour que l'identité soit
stable quand les données sous-jacentes n'ont pas changé, ou passer à une bibliothèque de state basée
sur des selectors (Redux, Zustand) pour un state à la fois volumineux et fréquemment mis à jour, car
elles permettent de souscrire à une tranche plutôt qu'à la valeur entière.

**Exemple :**
```jsx
// Nouvelle identité d'objet à chaque rendu, même si user/theme/settings n'ont pas changé :
<AppContext.Provider value={{ user, theme, settings }}>
// Chaque consommateur refait un rendu à chaque rendu du parent, quel que soit le champ qu'il lit.

// Corrigé : identité stable sauf si les données sous-jacentes ont réellement changé.
const value = useMemo(() => ({ user, theme, settings }), [user, theme, settings]);
<AppContext.Provider value={value}>
```

**Pourquoi c'est un piège :** "J'utilise Context correctement, les valeurs viennent simplement du
state" passe à côté du fait que le provider crée *lui-même* un tout nouvel objet valeur à chaque
rendu s'il n'est pas mémoïsé — Context n'est pas le problème, c'est un objet enveloppe non mémoïsé
qui lui est passé.

#### Q19. Comment fonctionnent les query keys dans React Query (TanStack Query), et pourquoi sont-elles une source classique de données périmées ou erronées ?
**Réponse :** La query key est à la fois l'*identité de cache* **et** le tableau de dépendances du
fetch : deux composants utilisant la même key partagent un seul résultat en cache et une seule requête
en vol, et quand la key change la bibliothèque la traite comme une requête différente, allant
chercher (ou servant le cache de) la nouvelle. La règle est donc : *chaque entrée utilisée par la
fonction de fetch doit figurer dans la key*. Omettez `page`, un filtre ou un id utilisateur et des
requêtes différentes entrent en collision sur une même entrée de cache — on affiche les données de la
page 1 sur la page 2, ou les données d'un tenant à un autre. Trois timers causent la plupart des
confusions : `staleTime` (combien de temps les données sont considérées fraîches et ne sont pas
re-fetchées au mount/focus — par défaut `0`, donc elles sont beaucoup re-fetchées), `gcTime` (combien
de temps les données en cache *inutilisées* sont conservées avant le garbage collection — 5 minutes
par défaut) et `refetchOnWindowFocus`. Après une mutation, le cache ne sait pas ce qui a changé : il
faut `invalidateQueries` (par préfixe de key) ou mettre à jour le cache avec `setQueryData`, sinon les
listes continuent d'afficher d'anciennes valeurs jusqu'à l'expiration de `staleTime`. Structurez les
keys hiérarchiquement (`["orders", "list",
{ status, page }]`) pour pouvoir invalider large ou étroit avec un seul appel.

**Exemple :**
```tsx
// Faux : la key ignore `status` et `page` -> chaque filtre partage une seule entrée de cache.
useQuery({ queryKey: ["orders"], queryFn: () => api.orders({ status, page }) });

// Juste : la key contient chaque entrée ; un changement de status/page est une requête différente.
const ordersKey = (status: string, page: number) => ["orders", "list", { status, page }] as const;
useQuery({ queryKey: ordersKey(status, page), queryFn: () => api.orders({ status, page }), staleTime: 30_000 });

// Après une mutation, invalider par préfixe pour que chaque liste en cache soit re-fetchée.
const qc = useQueryClient();
useMutation({
  mutationFn: api.cancelOrder,
  onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
});
```

**Pourquoi c'est un piège :** une mauvaise key ne lève pas d'erreur — elle retourne des données
plausibles d'*une autre* requête, et comme le cache masque le réseau, le bug n'apparaît que sur
certaines séquences de navigation. Il survit souvent à la review parce que `queryFn` fait une closure
sur les variables et "a l'air correct" (une règle ESLint, `exhaustive-deps` de
`@tanstack/eslint-plugin-query`, l'attrape). Voir S22 pour la moitié invalidation.

### UI asynchrone & React 19

#### Q20. Qu'est-ce que `Suspense`, et comment permet-il le code splitting ?
**Réponse :** `Suspense` permet à un arbre de composants d'"attendre" quelque chose (le plus souvent un
module de composant chargé paresseusement, via `React.lazy(() => import('./HeavyComponent'))`) et
d'afficher une UI de repli en attendant, sans que la logique de chargement soit passée manuellement
sous forme de state booléen et de rendu conditionnel. Combiné avec `React.lazy`, c'est le mécanisme
derrière le code splitting : le code du composant importé paresseusement n'est pas du tout inclus dans
le bundle JavaScript initial — il est récupéré comme un chunk séparé seulement quand cette partie de
l'arbre est réellement rendue — ce qui réduit la taille du bundle initial et le temps de chargement
pour des routes/fonctionnalités qu'une session utilisateur donnée ne visitera peut-être jamais,
laissant `Suspense` afficher un spinner ou un skeleton pendant la brève fenêtre où ce chunk se
télécharge.

**Exemple :**
```jsx
const HeavyEditor = React.lazy(() => import('./HeavyEditor'));

function Page() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyEditor />
    </Suspense>
  );
}
// Le code de HeavyEditor est un chunk séparé, récupéré seulement quand cet arbre le rend réellement.
```

**Pourquoi c'est un piège :** envelopper quelque chose dans `Suspense` sans réellement le code-splitter
via `React.lazy`/`import()` dynamique n'accomplit rien en soi — `Suspense` ne crée qu'une frontière
d'attente ; le gain de taille de bundle vient entièrement de l'import paresseux, pas de la frontière
elle-même.

#### Q21. Que capturent réellement les error boundaries React, et que ne capturent-elles explicitement pas ?
**Réponse :** Une error boundary (un composant classe implémentant `static getDerivedStateFromError`
et/ou `componentDidCatch`, car il n'existe pas d'équivalent en hook) capture les erreurs levées
pendant le rendu, dans les méthodes de cycle de vie et dans les constructeurs de l'arbre de composants
en dessous d'elle, remplaçant ce sous-arbre par une UI de repli au lieu de faire planter toute
l'application. Elle ne capture explicitement **pas** les erreurs dans les gestionnaires d'événements
(un `try`/`catch` dans le gestionnaire lui-même est le bon outil, puisqu'un gestionnaire d'événement
qui se déclenche après un rendu réussi ne fait pas partie du processus de rendu de React), le code
asynchrone (un `.then()`/`await` dans un `useEffect`, un callback `setTimeout` — même raisonnement,
il s'exécute hors de la phase de rendu que la boundary enveloppe), les erreurs pendant le rendu côté
serveur, ni les erreurs levées dans le code de rendu du fallback de l'error boundary elle-même.

**Exemple :**
```jsx
class ErrorBoundary extends React.Component {
  static getDerivedStateFromError(error) { return { hasError: true }; }
  render() { return this.state.hasError ? <Fallback /> : this.props.children; }
}

function Button() {
  const onClick = () => { throw new Error('boom'); }; // NON capturée par une ErrorBoundary au-dessus
  return <button onClick={onClick}>Click</button>;
}
```

**Pourquoi c'est un piège :** supposer qu'une error boundary enveloppant toute l'application est un
filet de sécurité pour *n'importe quelle* erreur non capturée — les gestionnaires d'événements et les
callbacks asynchrones s'exécutent hors de la phase de rendu que la boundary observe, ils ont donc
besoin de leur propre `try`/`catch` quelle que soit la hauteur dans l'arbre où se trouve une boundary.

#### Q22. Que changent les Actions, `useActionState`, `useOptimistic` et `use` de React 19 dans le code de formulaires et de data-fetching, et où sont les pièges ?
**Réponse :** React 19 fait de la boucle "soumettre, afficher pending, afficher l'erreur, mettre à
jour l'UI" une primitive intégrée au lieu de flags `useState` écrits à la main. Une **Action** est une
fonction (sync ou async) passée à `<form action={...}>` ou exécutée dans `startTransition` ; React
suit son état pending, réinitialise les champs non contrôlés en cas de succès et garde l'UI réactive
pendant son exécution. `useActionState` enveloppe une action et retourne `[state, formAction,
isPending]`, de sorte que l'erreur/le résultat retourné et le flag pending viennent d'un seul endroit.
`useOptimistic` permet d'afficher immédiatement le résultat *attendu* pendant que l'action est en
vol ; React écarte la valeur optimiste et affiche le vrai state quand la transition se termine — y
compris en faisant automatiquement un rollback si l'action lève une exception. `use(promise)` lit une
promise pendant le rendu (suspendant jusqu'à sa résolution, donc elle fonctionne avec `Suspense` et
les error boundaries) et `use(context)` peut être appelé conditionnellement, contrairement à
`useContext`. Les pièges : (1) la valeur optimiste n'est **valide que pendant la durée de la
transition** — si vous n'attendez pas (await) la vraie mutation *dans* l'action, elle revient
instantanément en arrière ; (2) une promise passée à `use` doit être **stable entre les rendus**
(créée dans un parent/loader ou mise en cache) — la créer inline pendant le rendu lance une nouvelle
requête à chaque rendu et boucle indéfiniment ; (3) les actions se résolvent *séquentiellement* par
formulaire/transition, donc une action lente retarde les suivantes ; (4) `useFormStatus` ne lit le
statut que du `<form>` *parent*, il doit donc vivre dans un composant enfant.

**Exemple :**
```tsx
function AddTodo({ todos, addTodo }: { todos: Todo[]; addTodo: (title: string) => Promise<Todo> }) {
  const [optimisticTodos, addOptimistic] = useOptimistic(
    todos,
    (current, title: string) => [...current, { id: crypto.randomUUID(), title, pending: true }],
  );

  async function action(formData: FormData) {
    const title = String(formData.get("title"));
    addOptimistic(title);            // affiché immédiatement
    await addTodo(title);            // doit être attendu dans l'action, sinon retour arrière immédiat
  }                                  // en cas d'exception, l'item optimiste disparaît automatiquement

  return (
    <form action={action}>
      <input name="title" required />
      <button>Add</button>
      <ul>{optimisticTodos.map(t => <li key={t.id} style={{ opacity: t.pending ? 0.5 : 1 }}>{t.title}</li>)}</ul>
    </form>
  );
}

// Piège avec use() : une nouvelle promise à chaque rendu -> suspend, résout, re-render, nouvelle promise ...
function Profile({ id }: { id: string }) {
  const user = use(fetch(`/api/users/${id}`).then(r => r.json()));   // faux : non stable
  return <h1>{user.name}</h1>;
}
```

**Pourquoi c'est un piège :** les nouvelles API ressemblent à du sucre mais changent *l'endroit* où
vit le state. Les développeurs gardent leurs flags `useState` `isLoading`/`error` et se retrouvent
avec deux sources de vérité, oublient que le state optimiste est transitoire (l'UI revient en arrière
d'un coup quand la mutation n'est pas attendue), ou créent la promise pour `use` inline et produisent
une boucle de suspend infinie. Notez aussi que l'UI optimiste est une *prédiction* : le serveur peut
la rejeter ou retourner un id différent, il faut donc réconcilier avec la vraie réponse (S19).

### TypeScript

#### Q23. Donnez un cas d'usage pratique des generics TypeScript dans une codebase React.
**Réponse :** Un hook de data-fetching typé est l'exemple canonique : `function useApi<T>(url: string):
{ data: T | null; loading: boolean; error: Error | null }` permet à chaque site d'appel d'obtenir une
inférence de types complète pour sa forme de réponse spécifique (`useApi<User>('/api/user')` donne à
`data` le type `User | null`) sans écrire un hook séparé par endpoint ni perdre la sûreté de typage
avec un wrapper de fetch générique typé `any`. Les composants génériques suivent la même idée — un
composant réutilisable `<Select<T>>` ou `<List<T>>` typé selon le type d'item qu'on lui donne, de
sorte que les consommateurs obtiennent une autocomplétion et une vérification de types correctes sur
`onSelect: (item: T) => void` quel que soit le `T` à chaque site d'appel, sans que le composant ait
besoin de connaître à l'avance tous les types qu'il pourrait un jour afficher.

**Exemple :**
```tsx
function useApi<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(url).then(r => r.json()).then((d: T) => { setData(d); setLoading(false); });
  }, [url]);
  return { data, loading };
}

const { data } = useApi<User>('/api/user'); // data: User | null, entièrement inféré
```

**Pourquoi c'est un piège :** écrire ce hook avec `any` au lieu d'un paramètre de type générique
"fonctionne" de la même façon à chaque site d'appel jusqu'à ce qu'un appelant déstructure un champ
qui n'existe pas — la version générique attrape ce décalage à la compilation ; `any` n'attrape rien
du tout.

#### Q24. Pourquoi préférer une discriminated union à plusieurs flags booléens pour modéliser l'état d'une requête ?
**Réponse :** Avec des booléens séparés (`isLoading`, `isError`, `data`, `error`), le système de types
autorise des combinaisons impossibles (`isLoading: true, isError: true` simultanément, ou `data`
présent alors que `isLoading` est aussi true) — rien n'empêche cet état invalide d'être construit, et
chaque consommateur doit se prémunir défensivement contre des combinaisons qui ne devraient pas se
produire mais le peuvent techniquement. Une discriminated union rend les états invalides réellement
non représentables : on ne peut être que dans exactement une des formes listées à la fois, et le
narrowing sur `status` dans un `switch` donne un accès type-safe à `data` uniquement dans la branche
`success` et à `error` uniquement dans la branche `error` — le compilateur impose les vraies
transitions valides de la machine à états au lieu que le code doive l'imposer manuellement partout où
l'état est lu.

**Exemple :**
```ts
// fragile
{ isLoading: boolean; isError: boolean; data: User | null; error: string | null }
// vs discriminated union
type RequestState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };
```

**Pourquoi c'est un piège :** modéliser l'état d'une requête avec plusieurs booléens indépendants
semble naturel — chaque nouvel état paraît ne demander qu'un flag de plus — mais rien n'empêche ces
flags d'être positionnés dans des combinaisons qui devraient être impossibles, et chaque consommateur
finit par se prémunir défensivement contre des états que le système de types aurait dû exclure
entièrement.

#### Q25. Pourquoi `unknown` est-il considéré comme plus sûr que `any` en TypeScript ?
**Réponse :** `any` exclut totalement une valeur de la vérification de types — on peut appeler
n'importe quelle méthode, accéder à n'importe quelle propriété, la passer n'importe où, et le
compilateur autorise tout cela sans erreur, même des opérations absurdes, réintroduisant
silencieusement exactement la classe d'erreurs de type à l'exécution que TypeScript existe pour
attraper. `unknown` accepte lui aussi n'importe quelle valeur qui lui est assignée, mais le
compilateur *refuse* de vous laisser en faire quoi que ce soit (appeler une méthode, accéder à une
propriété, la passer à un paramètre typé) tant que vous n'avez pas d'abord restreint son type — via
un type guard, une vérification `typeof`/`instanceof`, ou une assertion explicite. Cela fait de
`unknown` le bon type pour ce qui est réellement inconnu à la frontière (un payload JSON parsé, une
réponse d'API externe, l'erreur d'un bloc `catch`) — il force l'étape de narrowing/validation
(scénario S16) plutôt que de laisser une valeur non vérifiée circuler silencieusement dans le reste
de la codebase comme si elle était entièrement fiable.

**Exemple :**
```ts
function handle(x: any) { x.toUpperCase(); }   // compile — plante à l'exécution si x n'est pas une string
function handleSafe(x: unknown) {
  if (typeof x === 'string') x.toUpperCase();  // le compilateur impose d'abord cette vérification
}
```

**Pourquoi c'est un piège :** `any` "ressemble" à un type normal parce que TypeScript ne s'en plaint
jamais — ce silence est précisément le danger ; `unknown` porte le même manque d'information de type
initiale mais force l'étape de narrowing avant que toute opération soit autorisée à compiler.

#### Q26. Qu'apportent respectivement `as const`, `satisfies` et une vérification exhaustive avec `never` en TypeScript ?
**Réponse :** Ce sont trois outils pour conserver des *types littéraux précis* sans renoncer à la
vérification. **`as const`** fige un littéral : `["draft", "sent"] as const` a le type
`readonly ["draft", "sent"]` au lieu de `string[]`, et on peut en dériver une union
(`typeof STATUSES[number]`) pour que la liste des valeurs et le type ne divergent jamais.
**`satisfies`** valide qu'une expression *est conforme* à un type sans l'*élargir* à ce type : avec
une annotation de type (`const routes: Record<string, Route> = ...`) on perd les clés spécifiques et
les valeurs littérales ; avec `satisfies` on obtient toujours une erreur pour une mauvaise forme,
mais `routes.home` conserve son type exact et les fautes de frappe dans les clés sont toujours
attrapées. Une **vérification exhaustive `never`** (une branche `default` qui assigne la valeur à
`never`) fait échouer le compilateur quand un nouveau membre est ajouté à une union et qu'un `switch`
oublie de le gérer — transformant "on a oublié le nouveau statut quelque part" d'un bug de production
en une erreur de compilation. Piège connexe : un `enum` TypeScript est un objet runtime (les enums
numériques acceptent même n'importe quel nombre), donc pour la plupart du code applicatif une union de
string littérales dérivée d'un tableau `as const` est plus légère et plus sûre.

**Exemple :**
```ts
const STATUSES = ["draft", "sent", "paid"] as const;
type Status = typeof STATUSES[number];               // "draft" | "sent" | "paid"

const labels = {
  draft: "Draft",
  sent: "Sent",
  paid: "Paid",
} satisfies Record<Status, string>;                  // erreur si un statut manque ou est mal orthographié
labels.paid;                                          // typé chaîne "Paid", pas juste string

function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function color(s: Status): string {
  switch (s) {
    case "draft": return "gray";
    case "sent": return "blue";
    case "paid": return "green";
    default: return assertNever(s);                  // ajouter "void" à STATUSES casse le build ici
  }
}
```

**Pourquoi c'est un piège :** sans ces outils, le code compile avec un `string` large, une annotation
qui efface les littéraux, ou un `switch` avec un fall-through silencieux — et le cas manquant se
manifeste par un badge vide ou `undefined` en production. `as const` est aussi superficiel dans son
*intention* : il rend l'objet en lecture seule uniquement à la compilation, il n'est pas figé à
l'exécution (`Object.freeze` est l'outil runtime).

### Tests

#### Q27. Que faut-il réellement tester dans un composant React, selon la philosophie de React Testing Library ?
**Réponse :** Tester le comportement tel que l'utilisateur le vivrait — faire le rendu du composant,
interagir avec lui comme le ferait un utilisateur (cliquer, taper, trouver les éléments par texte
visible/rôle/label, pas par classe CSS ou implémentation interne), et vérifier ce qui est visible ou
déclenché en conséquence — plutôt que de tester des détails d'implémentation internes comme les
valeurs de state spécifiques d'un composant, les hooks qu'il appelle en interne, ou la forme exacte de
son arbre de rendu. Le raisonnement sous-jacent : les tests de détails d'implémentation cassent lors
d'un refactor valide qui ne change pas du tout le comportement visible par l'utilisateur (renommer
une variable de state interne, passer de `useState` à `useReducer` en interne), ce qui habitue
l'équipe à se méfier des tests en échec ou à les ignorer — une suite de tests doit échouer quand le
comportement casse réellement, et rester verte lors d'une restructuration interne qui ne change pas ce
que l'utilisateur voit ou peut faire.

**Exemple :**
```jsx
// Test de détail d'implémentation — casse lors d'un refactor interne valide.
expect(wrapper.state('isOpen')).toBe(true);

// Test de comportement — survit au même refactor.
expect(screen.getByRole('dialog')).toBeVisible();
```

**Pourquoi c'est un piège :** les tests de détails d'implémentation passent aussi facilement que les
tests de comportement quand tout va bien, donc la différence est invisible jusqu'à ce que le premier
refactor valide casse un mur de tests qui n'auraient pas dû s'en soucier — la confiance s'érode, et
les équipes se mettent à ignorer la CI rouge, ce qui est pire que de ne pas avoir de tests du tout.

## 🔴 Expert / Ouvert

### Performance

#### Q28. Une grande table de données devient nettement saccadée au scroll ou au filtrage. Détaillez le diagnostic et la correction.
Commencez par le Profiler des React DevTools pour voir ce qui se re-render réellement et combien de
temps cela prend — ne devinez pas. Constats courants, à peu près par ordre de probabilité : chaque
ligne refait un rendu à chaque frappe d'un input de filtre parce que les composants de ligne ne sont
pas mémoïsés (`React.memo`) ou parce qu'ils le sont mais reçoivent une nouvelle fonction/objet inline
en prop à chaque rendu (piège de Q12), donc la mémoïsation ne sert à rien ; l'ensemble (volumineux)
des données est rendu dans le DOM d'un coup plutôt que seulement les lignes visibles, donc la
performance de scroll est bornée par le nombre total de lignes, pas par le nombre de lignes visibles
— la solution ici est la virtualisation de liste (ne rendre que les lignes actuellement dans ou près
du viewport, par ex. `react-window`/`react-virtual`), qui est la correction au plus fort impact pour
une liste réellement grande, puisqu'elle rend le coût de rendu indépendant du nombre total d'items ;
et un calcul coûteux (tri, filtrage, agrégation) qui se ré-exécute à chaque rendu au lieu d'être
mémoïsé avec `useMemo` sur les entrées réelles qui l'affectent. La distinction de niveau senior :
profiler d'abord, corriger le goulot d'étranglement précis que le profiler montre réellement, plutôt
que d'envelopper tout par réflexe dans `memo`/`useMemo` — la sur-mémoïsation a son propre coût (Q13)
et n'aide pas si la virtualisation était la vraie correction nécessaire.

### State & couche de données

#### Q29. Comment choisir entre Context + `useReducer` et une bibliothèque de state dédiée (Redux, Zustand, React Query) ?
Partez du type de state réellement géré, car "quelle bibliothèque" est la mauvaise première question.
Le **server state** (données récupérées depuis une API, avec cache, revalidation, refetch en arrière-
plan, et états de chargement/erreur comme préoccupations de premier ordre) est un problème
fondamentalement différent du client state, et un outil dédié (React Query/TanStack Query, SWR) le
résout bien plus complètement que de le bricoler avec Context — c'est généralement l'adoption de
bibliothèque à plus forte valeur pour une application CRUD typique, indépendamment de la réponse
côté client state. Pour un véritable **client state** (état d'UI, préférences utilisateur, tout ce qui
ne reflète pas des données serveur) : Context + `useReducer` suffit et n'ajoute aucune dépendance
quand le state est petit, change peu souvent, et n'a pas le profil de performance qui déclenche le
problème de re-render de Q18 sur un large arbre de consommateurs. Recourez à une bibliothèque de
client state dédiée (Zustand, Redux) spécifiquement quand
le state est volumineux et fréquemment mis à jour avec de nombreux consommateurs n'ayant besoin que de
tranches de celui-ci (évitant le problème de re-render de tous les consommateurs de Q18 grâce aux
selectors), quand l'équipe a besoin d'un outillage de développement solide (time-travel debugging,
patterns de middleware bien établis) pour une machine à états réellement complexe, ou quand le même
state doit être lu/écrit depuis de nombreuses parties sans rapport d'une grande codebase d'une
manière où la composition ad hoc de Context devient difficile à raisonner. La réponse qui vaut en
entretien nomme la contrainte réelle qui motive le choix, et non une préférence de bibliothèque
énoncée comme si c'était un défaut universel.

#### Q30. Concevez un client d'API typé / une couche de data-fetching avec les generics TypeScript, avec une gestion d'erreurs appropriée.
Une fonction de requête générique typée selon la forme de réponse attendue (`function apiRequest<T>(url:
string, schema: ZodSchema<T>): Promise<T>`) qui effectue le fetch, vérifie explicitement le statut
HTTP (une réponse non-2xx n'est pas automatiquement une exception JavaScript — `fetch` ne rejette
qu'en cas d'échec réseau, pas sur 404/500), et — de façon cruciale pour une vraie sûreté de typage,
pas seulement une sûreté de typage déclarée — valide le JSON parsé avec un schéma runtime (Zod, ou
similaire) avant de le retourner typé `T`, plutôt que d'asserter simplement `as T` sur du JSON non
vérifié (le point `unknown`-vs-`any` de Q25 s'applique directement ici : une réponse externe est
`unknown` tant qu'elle n'a pas réellement été vérifiée, et `as T` sur un `unknown` non validé est une
promesse valable uniquement à la compilation que le runtime n'impose pas, ce qui est exactement
comment S16 se produit). Les erreurs sont modélisées comme un résultat en discriminated union (Q24)
plutôt que par des exceptions levées pour les modes d'échec attendus (une erreur de validation, un
404, un échec réseau ont chacun leur propre variante typée), de sorte que les appelants sont
contraints par le compilateur de traiter explicitement chaque cas via le narrowing sur `status`,
plutôt qu'un `try`/`catch` facile à oublier autour d'une erreur levée. Chaque endpoint spécifique
devient alors un wrapper fin et entièrement typé : `getUser(id: string) { return apiRequest(`/users/${id}`, userSchema); }`.

### Typage

#### Q31. Comment typer un composant de design system qui supporte une prop `as` (un `Button` polymorphe pouvant rendre `<a>`, `<button>` ou un `Link` de routeur) ?
L'objectif est que le composant accepte *les props de l'élément qu'il rend* et rejette les props que
cet élément n'a pas (`href` sur un `<button>`, `type` sur un `<a>`). L'approche naïve —
`props: any`, ou une union écrite à la main des props de chaque élément — perd soit la vérification,
soit ne passe pas à l'échelle. La solution idiomatique est un generic sur le type d'élément,
`C extends React.ElementType`, avec des props construites comme *vos propres props fusionnées avec
celles de l'élément choisi moins le chevauchement* :
`PolymorphicProps<C, Own> = Own & Omit<React.ComponentPropsWithoutRef<C>, keyof Own> & { as?: C }`.
Les appelants obtiennent alors l'autocomplétion de `href` quand `as="a"` et une erreur de compilation
quand ils passent `href` à un `button`. Ajoutez une variante `ref` via `ComponentPropsWithRef` ou le
`ref` de React 19 comme simple prop. Deux réserves : l'inférence sur des composants génériques avec
des conditional types compliqués devient lente et produit des erreurs illisibles, donc gardez le type
dans un seul helper bien testé ; et la flexibilité a un coût d'accessibilité, car `as="div"` avec
`onClick` perd la sémantique clavier et de rôle — le design system devrait restreindre `as` à un
ensemble d'éléments valides et intégrer l'accessibilité d'office (ou proposer des variantes explicites
comme `ButtonLink`) plutôt que de tout autoriser. Souvent l'alternative la plus maintenable à `as` est
la composition — un pattern `asChild` (Radix `Slot`) qui fusionne les props dans l'unique enfant — ou
des composants séparés partageant des styles, ce qui échange un peu de duplication contre des types
bien plus simples. Décidez selon le nombre de consommateurs : un design system public justifie le type
générique ; un bouton interne à une application le justifie rarement.

### Architecture

#### Q32. Quand adopteriez-vous les React Server Components (RSC), et que vous coûtent-ils ?
Les RSC font le rendu sur le serveur (à la requête ou au build) et envoient au client un arbre
sérialisé au lieu de JavaScript : un Server Component peut faire `await` directement sur une base de
données ou une API, son code et ses dépendances lourdes (un parseur Markdown, une bibliothèque de
dates) **ne sont jamais envoyés au navigateur**, et les secrets restent sur le serveur. Les Client
Components (marqués `"use client"`) restent nécessaires pour le state, les effets, les gestionnaires
d'événements et les API du navigateur, et ils s'hydratent comme d'habitude. Les bénéfices sont des
bundles plus petits, moins de cascades de requêtes côté client (les données sont récupérées à côté de
l'endroit où elles sont rendues, près de la source de données), et le streaming avec `Suspense`. Les
coûts sont réels : un **modèle mental à deux environnements** (ce qui s'exécute où, ce qui peut
traverser la frontière — uniquement des props sérialisables, pas de fonctions d'un Server vers un
Client Component sauf les Server Actions), une **dépendance à un framework** (en pratique le Next.js
App Router ou équivalent, avec une intégration bundler/routeur), des tests et un débogage local plus
difficiles, une infrastructure serveur et des sémantiques de cache à comprendre (mémoïsation par
requête, ce qui est mis en cache et quand c'est revalidé), et des moyens faciles de perdre le
bénéfice — un seul `"use client"` en haut d'un layout fait entrer dans le bundle client chaque import
en dessous. Je choisirais les RSC pour des pages riches en contenu ou en données où le premier
chargement et le SEO comptent et où l'équipe peut investir dans le framework ; je resterais sur une
SPA rendue côté client plus React Query pour une application authentifiée et très interactive derrière
un login (dashboards, éditeurs), où le SEO a peu de valeur et où la majeure partie de l'UI est de
toute façon du client state. Dans les deux cas, gardez la frontière délibérée : poussez `"use client"`
vers les feuilles (un bouton, un graphique), passez les données serveur en props, et mesurez la taille
du bundle et le time-to-interactive avant et après plutôt que de l'adopter par effet de mode.

#### Q33. Quand les micro-frontends sont-ils une bonne idée, et quelles sont les alternatives ?
Les micro-frontends découpent une application web en frontends construits et déployés indépendamment,
composés dans le navigateur (Module Federation, web components, iframes) ou à l'edge/serveur. Le vrai
problème qu'ils résolvent est *organisationnel* : de nombreuses équipes qui doivent livrer à leur
propre cadence sans coordonner la release d'un gros bundle, ou une migration progressive (une
application AngularJS legacy étranglée morceau par morceau vers React). Ils ne rendent pas une
application plus rapide ni plus simple ; le prix est des dépendances dupliquées sauf si elles sont
soigneusement partagées (deux React sur une page cassent les hooks), un look and feel incohérent, des
préoccupations transverses plus difficiles (auth, routing, analytics, gestion d'erreurs, un design
system partagé), un contrat d'intégration runtime versionné et testé comme une API, et plus
d'infrastructure (chaque fragment a son propre pipeline, et des tests end-to-end sont nécessaires à
travers eux). Alternatives qui apportent généralement l'autonomie des équipes à moindre coût : un
**monorepo modulaire** avec des frontières de modules imposées (nx/Turborepo, règles de lint pour les
restrictions d'import), un package de design system partagé publié avec des versions sémantiques, et
des feature flags avec du trunk-based development pour que les équipes déploient indépendamment *sans*
bundles runtime séparés. Ma règle : commencer par un monolithe modulaire ; n'introduire les
micro-frontends que lorsque l'organisation (10+ ingénieurs frontend, domaines et cycles de release
distincts) ou une migration exige des déploiements indépendants, choisir un petit nombre de tranches à
gros grain selon les domaines métier (jamais une par composant), et décider dès le départ comment le
routing, le state partagé (URL, événements — pas un store global partagé) et le design system
fonctionnent entre elles.

## 🎯 Scénarios réels

### S1. Un composant entre dans une boucle de re-render infinie, figeant l'onglet
- **Symptômes :** L'onglet du navigateur ne répond plus, React DevTools (s'il se charge) montre un
  compteur de rendus qui s'incrémente sans fin, et la console peut afficher une erreur "Maximum update
  depth exceeded".
- **Diagnostic :** Chercher un appel `setState` directement dans le corps du rendu (hors d'un
  gestionnaire d'événement ou d'un effet) — cela déclenche un re-render, qui appelle à nouveau le
  corps du rendu, qui appelle à nouveau `setState` — ou un `useEffect` dont le tableau de dépendances
  inclut une valeur que l'effet met lui-même à jour sans aucune garde, de sorte que la mise à jour de
  chaque exécution déclenche la suivante.
- **Exemple :**
  ```jsx
  function Broken() {
    const [count, setCount] = useState(0);
    setCount(count + 1); // appelé directement dans le corps du rendu — pas dans un effet/handler
    return <div>{count}</div>;
  }
  // Le rendu appelle setCount -> déclenche un re-render -> appelle à nouveau setCount -> ... à l'infini.
  ```
- **Résolution :** Déplacer l'appel `setState` dans un gestionnaire d'événement, ou dans un effet avec
  un tableau de dépendances qui reflète correctement uniquement ce qui doit le déclencher, en ajoutant
  une condition de garde si la mise à jour ne doit se produire qu'une fois ou sous des conditions
  précises plutôt qu'à chaque fois que les dépendances de l'effet sont réévaluées comme égales.
- **Prévention :** L'erreur React "Maximum update depth exceeded" et la règle ESLint
  `react-hooks/exhaustive-deps` existent toutes deux précisément pour attraper tôt cette classe de bug —
  gardez cette règle de lint activée plutôt que de la supprimer pour faire taire un avertissement sans
  le comprendre.

### S2. Un compteur affiché via `setInterval` dans `useEffect` montre toujours la même valeur, sans jamais s'incrémenter
- **Symptômes :** Un composant met en place `setInterval` dans un `useEffect` pour logger ou afficher
  périodiquement une valeur de state, mais la valeur affichée ne change jamais par rapport à celle du
  tout premier rendu, alors que le state réel ailleurs dans l'application s'est depuis mis à jour.
- **Diagnostic :** Stale closure classique (Q9) — le tableau de dépendances `[]` (vide) de l'effet
  signifie que le callback de l'interval a été créé exactement une fois, capturant la valeur de
  `count` du premier rendu, et comme l'effet ne se ré-exécute jamais, cette closure (et son `count`
  capturé) ne se met jamais à jour non plus.
- **Exemple :**
  ```jsx
  useEffect(() => {
    const id = setInterval(() => setCount(count + 1), 1000); // lit `count` depuis cette closure
    return () => clearInterval(id);
  }, []); // count n'apparaît jamais ici, donc cette closure — et son `count` — ne se rafraîchit jamais
  ```
- **Résolution :** Soit ajouter `count` au tableau de dépendances (en acceptant que l'interval soit
  démonté et recréé à chaque changement de `count`, ce qui est souvent acceptable), soit — la
  correction la plus robuste pour ce pattern précis — utiliser une mise à jour fonctionnelle du state
  (`setCount(c => c + 1)`) dans l'interval, qui n'a pas besoin de lire le `count` courant depuis la
  closure, de sorte que le tableau de dépendances de l'effet peut légitimement rester `[]`.
- **Prévention :** Traiter les avertissements `react-hooks/exhaustive-deps` comme des bugs à corriger,
  pas comme du bruit à supprimer avec un commentaire eslint-disable — la règle de lint est
  spécifiquement conçue pour attraper ce pattern exact de stale closure avant qu'il soit livré.

### S3. La console log en boucle "Can't perform a React state update on an unmounted component"
- **Symptômes :** Cet avertissement apparaît, généralement après avoir quitté rapidement une page, ou
  quand une réponse réseau lente revient après que l'utilisateur est déjà passé à autre chose.
- **Diagnostic :** Une opération asynchrone (un fetch, un callback de souscription) a été démarrée
  pendant que le composant était monté, et son `.then()`/callback appelle `setState` après que le
  composant a été démonté — l'opération asynchrone ne sait pas, et ne se soucie pas, que son composant
  a disparu au moment où elle se résout.
- **Exemple :**
  ```
  Warning: Can't perform a React state update on an unmounted component. This is a no-op,
  but it indicates a memory leak in your application. To fix, cancel all subscriptions and
  asynchronous tasks in a useEffect cleanup function.
      at UserProfile (UserProfile.jsx:14)
  ```
- **Résolution :** Utiliser un `AbortController` pour réellement annuler le fetch en vol au démontage
  (via la fonction de cleanup de l'effet), ou, si l'annulation n'est pas disponible pour la source
  asynchrone concernée, suivre un flag/ref "mounted" et le vérifier avant d'appeler `setState` dans le
  callback.
- **Prévention :** Tout effet qui démarre une opération asynchrone devrait avoir une fonction de
  cleanup qui traite ce qui se passe si cette opération se résout après le démontage — cela devrait
  faire partie standard de l'écriture de tout effet de data-fetching, et non être ajouté après coup
  une fois l'avertissement apparu.

### S4. Une grande table devient visiblement saccadée (frames perdues, scroll laggy) dès qu'elle atteint quelques milliers de lignes
- **Symptômes :** La performance de scroll est fluide avec un petit jeu de données mais se dégrade
  fortement quand le nombre de lignes atteint les milliers, bien avant que les données elles-mêmes
  soient considérées "volumineuses" selon les standards du backend.
- **Diagnostic :** Confirmé avec le Profiler (Q28) — tout le jeu de données est rendu en nœuds DOM
  réels d'un coup, donc le rendu initial comme tout travail déclenché par le scroll évoluent avec le
  nombre total de lignes plutôt qu'avec le nombre de lignes visibles.
- **Exemple :**
  ```
  # Flame graph du Profiler React DevTools : chaque <Row> commit à chaque frappe du filtre,
  # y compris les lignes dont les données n'ont pas changé — 4 000 rendus de Row commités par frappe,
  # alors que seulement ~20 lignes sont visibles à la fois dans le viewport.
  ```
- **Résolution :** Introduire la virtualisation de liste (`react-window` ou `react-virtual`), ne
  rendant que les lignes dans ou près du viewport actuel et recyclant les nœuds DOM pendant le scroll,
  ce qui rend le coût de rendu à peu près constant quelle que soit la taille totale du jeu de données.
- **Prévention :** Fixer un seuil explicite de nombre de lignes en code review/conception au-delà
  duquel tout nouveau composant liste ou table doit être virtualisé dès le départ, plutôt que d'être
  découvert comme un bug de performance quand le vrai volume de données arrive en production.

### S5. Taper dans un champ texte est laggy, avec un délai visible entre la frappe et l'apparition du caractère
- **Symptômes :** La réactivité perçue d'un input contrôlé se dégrade nettement, surtout dans un
  formulaire intégré à une page plus grande et complexe.
- **Diagnostic :** Vérifier ce qui d'autre re-render comme effet de bord du `onChange` de l'input — le
  `setState` de l'input lui-même est peu coûteux, mais si ce state vit dans (ou déclenche le re-render
  d') un grand composant parent dont le sous-arbre n'est pas mémoïsé, chaque frappe déclenche un
  re-render complet et coûteux de tout ce sous-arbre avant que le caractère n'apparaisse visuellement,
  puisque le comportement de rendu par défaut de React est synchrone.
- **Exemple :**
  ```jsx
  function Page() {
    const [text, setText] = useState('');
    return (
      <>
        <input value={text} onChange={e => setText(e.target.value)} />
        <ExpensiveChart data={text} /> {/* re-render synchrone à chaque frappe */}
      </>
    );
  }
  ```
- **Résolution :** Placer le state de l'input le plus localement possible (colocation, Q15) pour que
  son `setState` ne re-render que l'input lui-même et son environnement immédiat, pas toute la page ;
  mémoïser les sous-arbres frères/parents coûteux pour qu'ils ne se re-render pas simplement parce
  qu'un state local sans rapport a changé ; pour un travail aval réellement coûteux piloté par la
  valeur de l'input (par ex. filtrer une grande liste pendant la saisie), appliquer un debounce à ce
  travail ou l'envelopper dans `startTransition` (Q14) pour qu'il ne bloque pas le retour visuel
  immédiat de l'input lui-même.
- **Prévention :** Garder par défaut le state d'un input de formulaire colocalisé avec l'input, et
  traiter tout signalement "taper est laggy" comme une question de placement du state/mémoïsation à
  profiler immédiatement, plutôt que quelque chose à contourner par du throttling seul.

### S6. Modifier un petit morceau de state global (par ex. basculer le dark mode) provoque un re-render visible sur toute la page
- **Symptômes :** Le changement d'un seul réglage global (thème, langue, feature flag) provoque un
  flash/re-render visible sur de larges parties de l'UI qui n'ont rien à voir avec ce réglage.
- **Diagnostic :** Tout ce state vit dans un unique Context partagé dont les consommateurs couvrent la
  majeure partie de l'arbre de composants, et le comportement de Context où tous les consommateurs se
  re-render à chaque changement (Q18) signifie qu'un seul changement de valeur du Context re-render
  chaque consommateur, que celui-ci se soucie ou non du champ précis qui a changé.
- **Exemple :**
  ```jsx
  <AppContext.Provider value={{ theme, user, flags }}> {/* nouvel objet à chaque rendu */}
    <App /> {/* chaque consommateur dans l'arbre re-render au changement d'un seul champ */}
  </AppContext.Provider>
  ```
- **Résolution :** Découper le grand context unique en plusieurs contexts plus étroits (un
  `ThemeContext` séparé d'un `UserContext`, séparé d'un `FeatureFlagsContext`) pour qu'un changement de
  thème ne re-render que les consommateurs du thème, pas ceux des données utilisateur ; mémoïser
  l'objet valeur du context avec `useMemo` s'il est recréé inline à chaque rendu du provider que les
  données sous-jacentes aient changé ou non.
- **Prévention :** Éviter un unique context "app state" regroupant de nombreuses préoccupations sans
  rapport — concevoir les frontières de context autour de ce qui doit réellement changer ensemble, dès
  le départ, plutôt que de consolider par commodité et de découper plus tard quand le coût de
  re-render devient visible.

### S7. L'application plante en production avec une erreur de type à l'exécution, alors que le build TypeScript passe proprement
- **Symptômes :** `TypeScript compiled with 0 errors`, pourtant un outil de suivi d'erreurs en
  production montre un `TypeError: cannot read property 'x' of undefined` sur une valeur que le
  système de types prétendait toujours présente.
- **Diagnostic :** Chercher dans le code environnant des assertions de type `as` ou des `any` — une
  cause racine courante est une donnée venant d'une frontière externe (une réponse d'API,
  `localStorage`, une bibliothèque tierce sans types) qui est forcée par un cast (`as User`) au lieu
  d'être validée, de sorte que TypeScript a fait confiance à l'assertion à la compilation sans qu'aucune
  vérification runtime ne confirme jamais que la forme réelle correspondait.
- **Exemple :**
  ```ts
  const user = JSON.parse(response) as User; // le compilateur fait confiance sans condition
  user.email.toLowerCase(); // TypeError: Cannot read properties of undefined — l'API a omis `email`
  ```
- **Résolution :** Remplacer l'assertion non vérifiée par une validation runtime à la frontière (une
  bibliothèque de schémas comme Zod, ou au minimum des vérifications de forme explicites) pour qu'une
  réponse non conforme échoue bruyamment et précisément à la frontière, plutôt que de propager une
  valeur mal typée profondément dans l'application jusqu'à un plantage ailleurs sans rapport.
- **Prévention :** Traiter tout `as SomeType` sur des données provenant de l'extérieur du contrôle de
  la codebase comme un signal de code review nécessitant une justification — `unknown` plus une
  validation explicite (Q25, Q30) devrait être le pattern par défaut pour toute frontière de données
  externe, et non une mesure de durcissement occasionnelle.

### S8. Les résultats de recherche affichent parfois ceux d'une requête précédente, déjà abandonnée
- **Symptômes :** Taper rapidement dans un champ de recherche fait parfois revenir (ou clignoter) les
  résultats affichés vers ceux d'une requête antérieure, plus courte, alors que l'input lui-même
  montre le dernier texte saisi.
- **Diagnostic :** Une race condition entre des réponses réseau dans le désordre — chaque frappe
  déclenche un nouveau fetch, mais rien ne garantit que les réponses réseau se résolvent dans l'ordre
  d'envoi ; si l'effet fait naïvement `fetch(query).then(setResults)` à chaque frappe sans annulation
  ni vérification d'ordre, une réponse plus lente pour une requête antérieure peut se résoudre *après*
  une réponse plus rapide pour la dernière requête, écrasant les résultats corrects et plus récents
  par des résultats périmés.
- **Exemple :**
  ```jsx
  useEffect(() => {
    fetch(`/search?q=${query}`).then(r => r.json()).then(setResults);
    // pas d'annulation — une réponse lente pour une requête antérieure, plus courte, peut se résoudre après
    // une réponse plus rapide pour la dernière requête, l'écrasant avec des résultats périmés
  }, [query]);
  ```
- **Résolution :** Utiliser `AbortController` pour annuler la requête précédente quand une nouvelle
  démarre (la fonction de cleanup de l'effet abandonnant le fetch précédent, même mécanisme que S3),
  ou suivre à quelle requête correspond la réponse la plus récente et ignorer/écarter toute réponse
  qui ne correspond pas à la requête courante au moment où elle se résout.
- **Prévention :** Tout effet qui fetch selon une entrée changeant rapidement (recherche à la frappe,
  changements rapides de filtres) a besoin dès le départ d'une gestion explicite des réponses dans le
  désordre — c'est assez courant pour que de nombreuses bibliothèques de data-fetching (React Query
  incluse) la gèrent automatiquement, ce qui est en soi une raison de les préférer aux effets de fetch
  faits à la main pour ce pattern précis.

### S9. Un endpoint d'API est appelé deux fois pour ce qui devrait être un seul montage de composant
- **Symptômes :** L'onglet Réseau montre la même requête GET partant deux fois en succession rapide
  quand un composant fait son premier rendu, en développement spécifiquement (et l'équipe se demande si
  cela arrive aussi en production).
- **Diagnostic :** En développement, le `StrictMode` de React double-invoque délibérément certains
  comportements équivalents au cycle de vie (monter, démonter et remonter un composant, donc
  ré-exécuter les effets) spécifiquement pour aider à faire remonter les effets qui ne sont pas
  correctement nettoyés — c'est un comportement intentionnel, propre au développement, pas un bug de
  production, *si* la fonction de cleanup de l'effet annule/défait correctement le travail de la
  première invocation. Si cela arrive aussi en production, la cause réelle est plus probablement un
  tableau de dépendances manquant ou incorrect provoquant une vraie exécution en double de l'effet en
  dehors de la double invocation délibérée du `StrictMode`.
- **Exemple :**
  ```
  # Onglet Réseau en développement :
  GET /api/user   200   (déclenché au mount)
  GET /api/user   200   (déclenché à nouveau, ~0ms plus tard — double invocation délibérée du StrictMode)
  ```
- **Résolution :** Pour le cas `StrictMode`, cela indique généralement que l'effet de bord de l'effet
  (le fetch) n'a pas d'étape de cleanup et n'en a pas forcément besoin pour être "correct" en soi,
  mais il vaut la peine de confirmer que l'appel en double est réellement inoffensif (idempotent,
  sans écriture en double) — pour un effet qui modifie des données, c'est exactement le cas où un
  cleanup correct (annuler le premier fetch) compte. Pour un vrai doublon en production, corriger le
  tableau de dépendances ou ajouter une garde contre une requête en vol en double pour la même requête.
- **Prévention :** Ne pas désactiver `StrictMode` pour faire disparaître le symptôme — le traiter
  comme le signal voulu pour vérifier que le cleanup des effets est correct, puisque le bug sous-jacent
  qu'il révèle (un effet sans cleanup approprié) est un vrai problème latent même s'il ne duplique pas
  visiblement un appel en production aujourd'hui.

### S10. Un refactor pour passer une nouvelle valeur à travers cinq couches de composants devient un gros diff sujet aux erreurs
- **Symptômes :** Ajouter une nouvelle donnée dont un composant profondément imbriqué a besoin oblige
  à toucher l'interface de props de chaque composant intermédiaire sur le chemin, pour une donnée que
  ces composants intermédiaires n'utilisent pas par ailleurs.
- **Diagnostic :** C'est du prop drilling (Q15) arrivé au point où il est activement coûteux — la
  structure de l'arbre de composants ne correspond pas à la portée réelle de pertinence de la donnée,
  et chaque changement futur de cette valeur répète le même diff large et fragile.
- **Exemple :**
  ```jsx
  // Ajouter `locale` oblige à toucher chaque couche du chemin, même celles qui ne l'utilisent jamais :
  <Page locale={locale}>
    <Layout locale={locale}>
      <Sidebar locale={locale}>
        <Widget locale={locale} />
      </Sidebar>
    </Layout>
  </Page>
  ```
- **Résolution :** Pour des données réellement nécessaires largement et changeant rarement
  (utilisateur courant, thème, locale), introduire un Context à un ancêtre approprié pour que seuls
  les composants qui ont réellement besoin de la valeur la consomment directement, contournant
  entièrement les couches intermédiaires ; pour un state partagé qui change fréquemment ou volumineux,
  c'est le moment d'évaluer une bibliothèque de state dédiée (Q29) plutôt que de le résoudre avec
  Context seul.
- **Prévention :** Traiter "cette valeur doit-elle traverser des composants qui ne l'utilisent pas"
  comme une question de conception dès l'introduction d'une dépendance de données, et pas seulement
  quand le drilling s'est déjà étendu sur cinq couches et que le refactoring devient coûteux.

### S11. Une erreur levée dans le gestionnaire `onClick` d'un bouton fait planter toute la page au lieu d'être capturée par l'error boundary de l'application
- **Symptômes :** L'équipe a ajouté une error boundary enveloppant l'application spécifiquement pour
  éviter un plantage de page entière sur des erreurs inattendues, mais un bug dans un gestionnaire
  `onClick` produit toujours un écran blanc (ou une erreur console non gérée) au lieu de l'UI de repli
  attendue.
- **Diagnostic :** Les error boundaries ne capturent pas les erreurs des gestionnaires d'événements
  par conception (Q21) — le gestionnaire s'exécute hors de la phase de rendu de React, après un rendu
  réussi, ce n'est donc simplement pas quelque chose que le mécanisme `componentDidCatch` de la
  boundary observe.
- **Exemple :**
  ```jsx
  <ErrorBoundary>
    <button onClick={() => { throw new Error('boom'); }}>Click</button>
  </ErrorBoundary>
  // La boundary ne voit jamais cela — elle n'enveloppe que le rendu/cycle de vie, pas les gestionnaires d'événements.
  ```
- **Résolution :** Ajouter un `try`/`catch` explicite dans le gestionnaire d'événement lui-même (ou
  la fonction qu'il appelle) pour tout ce qui peut raisonnablement lever une exception, en traitant
  l'erreur localement (affichage d'un message inline, logging) plutôt que d'attendre que la boundary la
  capture.
- **Prévention :** Documenter clairement (dans les conventions d'équipe, pas seulement en savoir
  tribal) que les error boundaries ne couvrent que le chemin rendu/cycle de vie, et que les
  gestionnaires d'événements et le code asynchrone ont besoin de leur propre gestion d'erreurs
  explicite — c'est un malentendu réellement courant qui mérite d'être signalé directement lors de
  l'onboarding ou de la code review la première fois qu'il se présente.

### S12. Le temps de chargement initial de la page est lent, et l'onglet Réseau montre un unique très gros bundle JavaScript
- **Symptômes :** Le time-to-interactive est élevé même sur une connexion rapide, et le bundle
  analyzer montre un seul gros `main.js` contenant du code de routes/fonctionnalités que la plupart des
  utilisateurs sur cette page initiale ne visitent jamais.
- **Diagnostic :** Aucun code splitting n'est en place — chaque route et fonctionnalité, y compris
  celles rarement utilisées (un panneau d'admin, une page de réglages, la dépendance lourde d'une
  modale rarement ouverte), est incluse dans le chargement initial que la page courante en ait besoin
  ou non.
- **Exemple :**
  ```
  $ npx source-map-explorer build/static/js/main.*.js
  # main.js: 3.8 MB — inclut le panneau d'admin, l'éditeur de texte riche et une bibliothèque de
  # graphiques, dont aucun n'est jamais rendu par la landing page (la route la plus visitée).
  ```
- **Résolution :** Introduire au minimum un code splitting au niveau des routes avec `React.lazy` et
  `Suspense` (Q20), pour que le code de chaque route soit un chunk séparé récupéré seulement lors de la
  navigation ; pour les fonctionnalités individuelles particulièrement lourdes au sein d'une route (un
  éditeur de texte riche, une bibliothèque de graphiques), les extraire aussi et les charger
  paresseusement à l'interaction (par ex. seulement quand un onglet précis est ouvert) plutôt que de
  les inclure dans la route qui contient simplement l'option de les ouvrir.
- **Prévention :** Exécuter un bundle analyzer dans le processus régulier de build/review (pas
  seulement une fois, rétroactivement) pour qu'une grosse nouvelle dépendance ajoutée au bundle
  initial soit attrapée dès la PR qui l'introduit.

### S13. Un refactor qui ne change aucun comportement visible par l'utilisateur casse une grande partie de la suite de tests
- **Symptômes :** Renommer une variable de state interne, convertir un composant de `useState` à
  `useReducer` en interne, ou restructurer la façon dont un composant est composé en interne — rien de
  tout cela ne change ce que l'utilisateur voit ou peut faire — fait échouer de nombreux tests.
- **Diagnostic :** La suite de tests vérifie des détails d'implémentation (forme du state interne,
  appels de méthodes internes spécifiques, structure d'arbre de composants en shallow rendering) plutôt
  que le comportement observable par l'utilisateur — l'anti-pattern décrit en Q27, souvent issu
  d'utilitaires/patterns de test qui encouragent à fouiller dans les internes d'un composant plutôt que
  d'interagir avec lui comme le ferait un utilisateur.
- **Exemple :**
  ```jsx
  // Casse lors d'un refactor interne valide de useState vers useReducer :
  expect(wrapper.instance().state.isOpen).toBe(true);

  // Survit au même refactor :
  expect(screen.getByRole('dialog')).toBeVisible();
  ```
- **Résolution :** Réécrire les tests fragiles pour qu'ils interagissent avec le rendu comme le
  ferait un utilisateur (trouver par rôle/texte/label, cliquer, taper, vérifier ce qui est visible),
  ce qui devrait alors survivre au refactor interne sans changement puisque le comportement visible par
  l'utilisateur n'a réellement pas changé.
- **Prévention :** Adopter les priorités de requêtes de Testing Library (préférer
  `getByRole`/`getByLabelText` à `getByTestId`, et préférer fortement l'un ou l'autre à la fouille dans
  les internes du composant) comme convention d'équipe dès le départ, et considérer "ce test passe-t-il
  encore après un refactor valide qui préserve le comportement" comme le vrai critère d'un bon test, et
  non "passe-t-il maintenant".

### S14. Les éléments d'une liste réordonnable affichent parfois un mauvais contenu, ou perdent leur state d'input local, après un réordonnancement
- **Symptômes :** Une liste en drag-to-reorder, ou une liste où des éléments peuvent être
  insérés/supprimés au milieu, montre un décalage après réordonnancement — l'état d'une case à cocher
  d'un élément, ou la valeur saisie dans un input, apparaît attaché à la mauvaise ligne après le
  réordonnancement.
- **Diagnostic :** Vérifier la prop `key` utilisée pour la liste — c'est le symptôme classique de
  l'utilisation de l'index du tableau comme `key` pour une liste qui se réordonne : React associe les
  nœuds DOM (et leur state interne) aux positions de la liste par key d'un rendu à l'autre, et si la
  key est l'index plutôt qu'un identifiant stable par élément, réordonner les données sous-jacentes ne
  réordonne pas réellement quel nœud DOM/state React associe à quel élément — cela change seulement
  quelles données sont rendues à chaque index existant, laissant tout state local par élément derrière
  à l'ancienne position.
- **Exemple :**
  ```jsx
  {todos.map((todo, i) => (
    <TodoRow key={i} todo={todo} /> // réordonner `todos` ne réordonne pas quel nœud DOM/state
  ))}                                // React associe à quel élément — cela re-render simplement
                                     // le même index de nœud avec des données différentes
  ```
- **Résolution :** Utiliser un identifiant stable et unique issu des données réelles (un ID de base
  de données, un UUID) comme `key`, et non l'index du tableau, pour que React suive correctement quelle
  instance rendue correspond à quel élément logique à travers réordonnancements, insertions et
  suppressions.
- **Prévention :** Traiter "l'index du tableau comme key" comme un anti-pattern signalé par le lint
  pour toute liste qui peut être réordonnée, filtrée, ou avoir des éléments insérés/supprimés ailleurs
  qu'à la fin — c'est un choix correct et inoffensif uniquement pour une liste réellement statique, en
  ajout seul, jamais réordonnée, et cette exception est assez étroite pour que le réflexe par défaut d'un
  vrai ID soit l'habitude la plus sûre dans tous les cas.

### S15. La valeur affichée par un composant dérive silencieusement de la prop qu'il était censé refléter
- **Symptômes :** Un composant qui copie une prop entrante dans un state local (pour permettre une
  édition locale avant sauvegarde) affiche parfois des données périmées après la mise à jour de la prop
  ailleurs, ou perd une modification locale en cours de l'utilisateur quand la prop se met à jour pour
  une raison sans rapport.
- **Diagnostic :** C'est exactement l'anti-pattern de Q16 — synchroniser une prop dans le state via
  `useEffect` crée deux sources de vérité, et la synchronisation par effet introduit un écart de cycle
  de rendu (et un risque d'écrasement) entre la valeur courante réelle de la prop et le state local qui
  la reflète.
- **Exemple :**
  ```jsx
  const [draft, setDraft] = useState(props.value);
  useEffect(() => { setDraft(props.value); }, [props.value]);
  // Une mise à jour de prop arrivant entre "l'utilisateur commence à éditer" et "l'effet s'exécute" peut
  // écraser silencieusement sa modification en cours, ou afficher brièvement l'ancienne valeur à l'écran.
  ```
- **Résolution :** Si le composant n'a pas réellement besoin de diverger de la prop (il ne fait que
  l'afficher), supprimer entièrement le couple state local/effet et dériver la valeur affichée
  directement de la prop pendant le rendu. Si une divergence locale est réellement nécessaire (un
  brouillon éditable), utiliser une prop `key` sur le composant liée à ce qui identifie "une nouvelle
  valeur source" (par ex. l'ID de l'entité) pour que React remonte le composant avec un state local
  neuf exactement quand la source change, plutôt que d'essayer de réconcilier l'ancien state local avec
  une nouvelle prop via un effet.
- **Prévention :** Traiter "un state local initialisé depuis une prop, gardé synchronisé via
  `useEffect`" comme une odeur de conception à questionner immédiatement en review — c'est rarement la
  solution correcte la plus simple au problème qui l'a motivée, et le pattern `key`-remount ou la
  simple dérivation la remplace presque toujours plus simplement et plus correctement.

### S16. Le build TypeScript est propre, mais l'application plante au parsing de la réponse d'une API tierce
- **Symptômes :** Une API externe récemment intégrée retourne parfois un champ à `null` là où
  l'interface TypeScript le déclare comme un `string` obligatoire, et l'application plante en essayant
  d'appeler une méthode de string dessus — le compilateur ne l'a jamais signalé car il n'a aucun moyen
  de vérifier qu'une réponse HTTP externe correspond réellement à une interface écrite à la main.
- **Diagnostic :** L'interface décrivant la réponse de l'API a été écrite à la main (ou générée une
  fois à partir d'un exemple de réponse) et assertée sur le JSON parsé, plutôt que validée — les types
  TypeScript sont effacés à la compilation (module 1, le point sur l'effacement de Q3 s'applique ici par
  analogie) et n'offrent aucune garantie à l'exécution ; un décalage entre le type déclaré et la forme
  réelle de la réponse est invisible pour le compilateur et ne se manifeste que lorsque la donnée non
  conforme est réellement utilisée.
- **Exemple :**
  ```ts
  interface ApiUser { id: string; email: string; } // écrit à la main, jamais réellement vérifié
  const user = (await res.json()) as ApiUser;
  user.email.toLowerCase(); // l'API retourne `email: null` pour les comptes non vérifiés — plante ici
  ```
- **Résolution :** Ajouter une validation de schéma runtime (Zod, ou équivalent) au moment où la
  réponse est parsée, pour qu'un décalage de forme soit attrapé immédiatement avec une erreur claire
  identifiant exactement quel champ ne correspondait pas, au lieu de se manifester plus tard par un
  plantage d'apparence sans rapport, profondément dans l'arbre de composants ; décider explicitement (et
  typer en conséquence, par ex. `string | null`) comment le champ doit réellement être traité une fois
  sa vraie nullabilité connue.
- **Prévention :** Toute donnée traversant une frontière de confiance depuis l'extérieur du contrôle
  de la codebase (une API tierce, en particulier dont l'équipe ne contrôle pas le contrat) devrait être
  traitée comme `unknown` et validée à la frontière par défaut (Q25, Q30) — une interface écrite à la
  main sans vérification runtime est une promesse que le compilateur fait au nom de la codebase et qu'il
  n'a aucune capacité réelle de tenir.

### S17. La console affiche "Text content does not match server-rendered HTML" et la page clignote ou s'affiche mal après le chargement
- **Symptômes :** Sur une page rendue côté serveur (Next.js/Remix), la console logue `Hydration failed
  because the server rendered HTML didn't match the client` (ou "Text content does not match").
  Les utilisateurs voient un flash de la mauvaise valeur — la mauvaise heure, un header déconnecté pour
  un utilisateur connecté — et parfois React écarte le HTML serveur et re-render tout le sous-arbre
  côté client, perdant le bénéfice de performance du SSR. Cela ne se reproduit jamais dans un build de
  dev purement rendu côté client.
- **Diagnostic :** L'hydratation exige que le *premier rendu client* produise exactement le balisage
  envoyé par le serveur. Tout ce qui diffère entre les deux environnements casse cela : `Date.now()`,
  `new Date()` formaté dans le fuseau horaire du serveur vs celui du navigateur,
  `Math.random()`/`crypto.randomUUID()` pour des ids, des vérifications `window`/`localStorage` (branches
  `typeof window !== "undefined"`), le formatage selon la locale, ou un imbrication HTML invalide (un
  `<div>` dans un `<p>` que le navigateur "répare"). Lire le diff affiché dans l'overlay de dev pour
  trouver l'élément, puis chercher l'une de ces entrées dans son chemin de rendu.
- **Exemple :**
  ```tsx
  function Greeting() {
    const hour = new Date().getHours();                 // serveur : UTC, client : fuseau horaire de l'utilisateur
    const theme = localStorage.getItem("theme") ?? "light";  // lève une exception sur le serveur / diffère côté client
    return <p className={theme}>{hour < 12 ? "Good morning" : "Good afternoon"}</p>;
  }
  ```
- **Résolution :** Rendre le premier rendu déterministe et déplacer les valeurs spécifiques à
  l'environnement après l'hydratation : lire les données propres au navigateur dans `useEffect` (le
  state démarre avec la valeur par défaut sûre côté serveur et est mis à jour une fois monté), utiliser
  `useId` pour les ids générés, passer le timestamp/la locale calculés côté serveur en prop pour que les
  deux côtés formatent la même valeur, et corriger l'imbrication invalide. Pour un widget réellement
  client-only, le rendre via un wrapper client-only (import dynamique avec SSR désactivé) ou utiliser
  `suppressHydrationWarning` uniquement pour des différences inévitables sur un seul élément comme un
  timestamp. Vérifier que la console est propre sur un rechargement forcé avec le build de production.
- **Prévention :** Linter `window`/`Date.now`/`Math.random` dans les chemins de rendu des composants
  SSR, exécuter la suite E2E contre le build SSR de production et échouer sur les erreurs d'hydratation
  de la console, et traiter "le rendu doit être pur et identique des deux côtés" comme une règle de
  conception de composant (Q6).

### S18. Chaque frappe dans un champ de formulaire fait perdre le focus après un caractère
- **Symptômes :** Dans un formulaire de réglages, taper dans un input fonctionne pour un caractère puis
  le curseur disparaît ; l'utilisateur doit cliquer à nouveau pour chaque caractère. Le state local
  dans le champ (une position de scroll, un dropdown ouvert) se réinitialise aussi à chaque frappe. Le
  bug est apparu après qu'un développeur a "rangé" le fichier en extrayant un sous-composant.
- **Diagnostic :** L'input est **démonté puis remonté** à chaque rendu. React identifie un composant
  par son *type* à une position de l'arbre ; si une fonction composant est définie *à l'intérieur* du
  corps d'un autre composant, c'est une toute nouvelle fonction (un nouveau type) à chaque rendu du
  parent, donc React écarte l'ancien sous-arbre — nœud DOM, focus et state inclus — et en construit un
  nouveau. Le parent re-render à chaque frappe car le state y vit. Confirmer dans le Profiler ou en
  loggant dans un effet avec des deps `[]` dans l'enfant : il se déclenche à chaque frappe (la règle
  key/identité de Q11 s'applique aussi aux types).
- **Exemple :**
  ```tsx
  function Settings() {
    const [name, setName] = useState("");

    function NameField() {                     // nouveau type de composant à chaque rendu de Settings
      return <input value={name} onChange={e => setName(e.target.value)} />;
    }

    return <NameField />;                      // démonté et remonté à chaque frappe
  }
  ```
- **Résolution :** Définir le composant au niveau du module et lui passer en props ce dont il a besoin
  (ou l'appeler comme une simple fonction retournant du JSX s'il doit faire une closure sur des valeurs
  locales, ce qui évite de créer un nouveau type de composant). Vérifier en tapant une longue chaîne
  sans perdre le focus et avec un log d'effet de mount qui ne se déclenche qu'une fois.
- **Prévention :** Activer `react/no-unstable-nested-components` dans ESLint, relire tout composant
  déclaré à l'intérieur d'un autre, et colocaliser les petits sous-composants dans le même *fichier* —
  pas dans la même fonction.

### S19. Un bouton "like" avec mise à jour optimiste clignote et affiche finalement un mauvais compteur
- **Symptômes :** Les utilisateurs double-cliquent sur un bouton like. Le compteur monte, redescend,
  remonte, puis se stabilise sur une valeur qui ne correspond pas au serveur après un rafraîchissement.
  Sur des connexions mobiles instables, l'UI affiche "liked" alors que la requête a échoué et que rien
  n'a été sauvegardé.
- **Diagnostic :** La mise à jour optimiste écrit dans le cache/state mais ne gère pas trois choses :
  (1) les **refetches en vol** qui se terminent après l'écriture optimiste et l'écrasent avec l'ancienne
  valeur serveur (le clignotement), (2) le **rollback** quand la requête échoue — sans `onError`
  restaurant la valeur précédente, le mauvais état reste, et (3) les **mutations concurrentes** dont les
  réponses arrivent dans le désordre, chacune appliquant un résultat calculé à partir d'un snapshot
  périmé (la réserve de Q22 : les valeurs optimistes sont des prédictions). Reproduire avec l'onglet
  Réseau bridé et des requêtes retardées de façon inégale.
- **Exemple :**
  ```tsx
  useMutation({
    mutationFn: api.like,
    onMutate: (id) => {
      qc.setQueryData<Post>(["post", id], p => p && { ...p, likes: p.likes + 1 });   // pas de snapshot, pas d'annulation
    },
    // pas de rollback onError ; pas d'invalidation onSettled
  });
  ```
- **Résolution :** Suivre le pattern optimiste complet : dans `onMutate`, annuler les refetches en
  cours pour cette key (`await qc.cancelQueries`), faire un snapshot de la valeur précédente et le
  retourner comme contexte ; dans `onError`, restaurer le snapshot ; dans `onSettled`, invalider la key
  pour que le cache converge vers la vérité du serveur. Empêcher la double soumission en désactivant le
  bouton pendant pending, et envoyer une clé d'idempotence ou un *état* désiré (`liked: true`) plutôt
  qu'un incrément pour que les retries ne comptent pas deux fois. Vérifier avec un test en réseau bridé :
  clics rapides, puis échec forcé — l'UI revient à l'état correct.
- **Prévention :** Mettre les mutations optimistes dans un unique pattern de hook partagé, rendre les
  mutations idempotentes côté serveur, et ajouter un test avec une réponse mock retardée/échouée pour
  chaque interaction optimiste.

### S20. Le bundle JavaScript initial a doublé après un refactor "inoffensif" ; le score Lighthouse a chuté
- **Symptômes :** Après l'ajout d'un petit import utilitaire, le bundle principal est passé d'environ
  300 KB à environ 900 KB (gzip), le temps de premier chargement sur mobile a glissé de plusieurs
  secondes, et le contrôle de taille de bundle de la CI (ou Lighthouse) a commencé à alerter. Le code
  modifié n'importe qu'une icône et une fonction utilitaire.
- **Diagnostic :** Ouvrir un bundle analyzer (`vite-bundle-visualizer`, `webpack-bundle-analyzer`,
  `source-map-explorer`) et trouver le gros chunk. Coupables typiques : un **barrel file**
  (`components/index.ts` réexportant tout) ou un package dont l'entrée réexporte des milliers de
  modules (une bibliothèque d'icônes, `lodash` au lieu de `lodash-es`), où le bundler ne peut pas
  prouver l'absence d'effets de bord et garde tout, neutralisant le tree-shaking ; une bibliothèque
  lourde (un graphique ou un éditeur) tirée dans le chunk initial parce qu'elle est importée
  statiquement ; ou une frontière Server/Client placée trop haut. Vérifier `sideEffects` dans le
  package.json et la manière dont l'import est écrit.
- **Exemple :**
  ```ts
  import { format } from "lodash";                    // toute la bibliothèque (CommonJS, non tree-shakable)
  import { Icon } from "@/components";                // barrel : tire chaque composant et leurs dépendances
  import { HugeChart } from "./HugeChart";            // import statique : dans le bundle initial
  ```
- **Résolution :** Importer au chemin granulaire (`import format from "lodash/format"`, `lodash-es`, ou
  les points d'entrée par icône de la bibliothèque), importer depuis le fichier du composant plutôt que
  depuis le barrel, définir `"sideEffects": false` là où c'est valide, et charger paresseusement les
  modules lourds, sous la ligne de flottaison ou au niveau des routes avec `React.lazy` + `Suspense`
  (Q20). Relancer l'analyzer et confirmer que le chunk initial revient à la baseline.
- **Prévention :** Un **budget de taille de bundle en CI** (`size-limit` ou bundlesize) qui fait
  échouer la PR, une règle ESLint restreignant les imports de barrels/grosses bibliothèques, et une
  revue périodique de l'analyzer ; préférer des bibliothèques plus petites ou des API natives (`Intl`,
  `Date`) aux dépendances lourdes pour de petits besoins.

### S21. Une application single-page longue durée ralentit et sa mémoire croît régulièrement jusqu'au plantage de l'onglet
- **Symptômes :** Un dashboard laissé ouvert sur un écran mural pendant une journée devient lent et
  finit par planter ("Aw, Snap"). Le Gestionnaire de tâches de Chrome montre la mémoire croissant à
  chaque rafraîchissement de données ou changement de route ; redimensionner ou naviguer fait se
  déclencher les handlers plusieurs fois.
- **Diagnostic :** Prendre des **heap snapshots** (DevTools → Memory) avant et après avoir répété une
  action comme naviguer ailleurs puis revenir, et comparer : des nombres croissants de nœuds DOM
  détachés, d'event listeners, de closures ou de tableaux indiquent ce qui est retenu. Les causes
  habituelles sont des effets qui enregistrent un listener, un interval ou une souscription
  (`window.addEventListener("resize", ...)`, un WebSocket, un `subscribe` de store) sans fonction de
  cleanup (Q10), de sorte que chaque mount en ajoute un autre qui capture aussi les props/state du
  composant dans sa closure ; des caches ou tableaux non bornés qui ne font que s'accroître (un journal
  de messages jamais élagué) ; et des singletons au niveau module retenant des références de composants.
- **Exemple :**
  ```tsx
  useEffect(() => {
    const onTick = (m: Message) => setMessages(prev => [...prev, m]);   // croît indéfiniment
    socket.on("message", onTick);                                       // jamais retiré
  }, []);                                                               // chaque remount ajoute un autre listener
  ```
- **Résolution :** Retourner un cleanup qui retire le listener (`return () => socket.off("message", onTick)`),
  plafonner les collections (garder les N derniers messages, ou virtualiser et paginer), fermer les
  sockets et annuler les fetches dans le cleanup, et supprimer les références des caches au niveau
  module au démontage. Vérifier en répétant la comparaison de heap snapshots sur 50 navigations : la
  taille retenue reste plate et le nombre de listeners ne grimpe plus.
- **Prévention :** Le Strict Mode en développement double-invoque les effets, ce qui expose tôt les
  cleanups manquants — le garder activé. Préférer les bibliothèques qui gèrent le cycle de vie des
  souscriptions (React Query, `useSyncExternalStore`), ajouter un soak test pour les écrans de longue
  durée, et relire tout `addEventListener`/`setInterval`/`subscribe` dans un effet pour vérifier son
  pendant.

### S22. Après modification d'un enregistrement, la page de liste affiche encore les anciennes données jusqu'à ce que l'utilisateur recharge
- **Symptômes :** Un utilisateur renomme un client dans un formulaire et revient à la liste des
  clients, qui affiche toujours l'ancien nom. Un rafraîchissement règle le problème. Parfois la page de
  détail est à jour mais la liste, un widget de dashboard et un dropdown ailleurs ne le sont pas.
- **Diagnostic :** Avec un cache de server state (React Query/SWR), le cache conserve chaque requête
  sous sa key et ne sait pas qu'une mutation a modifié les données sous-jacentes (Q19). Ni
  `invalidateQueries` ni `setQueryData` n'a été appelé pour *toutes* les keys qui affichent
  l'enregistrement, ou l'invalidation a utilisé une key qui ne correspondait pas au préfixe de la liste
  en cache (`["customers"]` vs `["customer-list", { page }]`). Inspecter le cache dans les React Query
  DevTools : la requête de liste est `fresh` pendant la fenêtre `staleTime` et ne se re-fetch jamais au
  remount.
- **Exemple :**
  ```tsx
  const update = useMutation({ mutationFn: api.updateCustomer });          // aucune gestion du cache
  // liste :   useQuery({ queryKey: ["customer-list", { page }], staleTime: 5 * 60_000, ... })
  // détail :  useQuery({ queryKey: ["customer", id], ... })
  ```
- **Résolution :** Dans `onSuccess`, invalider par préfixe hiérarchique — `qc.invalidateQueries({ queryKey: ["customers"] })`
  — après avoir restructuré les keys en `["customers", "list", {...}]` et `["customers", "detail", id]` ;
  pour un retour instantané, écrire l'entité retournée avec `setQueryData` et invalider les listes.
  Vérifier avec un test : muter, revenir en arrière et vérifier que le nouveau nom s'affiche sans
  rechargement.
- **Prévention :** Centraliser des factories de keys (`customerKeys.all`, `.list()`, `.detail(id)`) à
  côté des fonctions d'API, pour que keys et invalidations ne puissent pas dériver ; garder `staleTime`
  délibéré plutôt que grand "pour économiser des requêtes" ; et faire de "quelles requêtes affichent
  cette entité ?" un point de checklist pour chaque mutation.

## 📌 Cheat-sheet

- **Hooks** : le même bénéfice de logique avec état regroupée que les classes ne pouvaient pas offrir sans wrapper hell ; doivent être appelés inconditionnellement, dans le même ordre à chaque rendu.
- **`useState` vs `useRef`** : le state déclenche un re-render et pilote l'UI ; la ref persiste de façon mutable sans en déclencher — à utiliser pour les nœuds DOM, timers, valeurs hors UI.
- **Stale closures** : les valeurs capturées par un effet sont figées à sa création ; deps `[]` + lecture d'une valeur qui change = bug. Préférer les mises à jour fonctionnelles (`setX(x => ...)`) pour l'éviter.
- **Cleanup d'effet** : obligatoire pour tout ce qui persiste au-delà d'une exécution — souscriptions, intervals, listeners, fetches en vol (`AbortController`).
- **`useMemo`/`useCallback`** : mémoïsent les calculs coûteux / une identité de fonction stable pour les enfants mémoïsés — profiler avant d'appliquer, ne pas en faire un défaut partout.
- **`React.memo`** : comparaison shallow des props ; inutile si le parent passe de nouveaux objets/fonctions inline à chaque rendu — mémoïser à la source, pas seulement chez le récepteur.
- **`key`** : ID stable par élément, jamais l'index du tableau pour une liste réordonnable/mutable — mauvaise key = state/contenu attaché à la mauvaise ligne.
- **Context** : tous les consommateurs re-render à tout changement de valeur — découper en contexts étroits et mémoïser l'objet valeur pour un state fréquemment mis à jour et largement consommé.
- **Ne pas synchroniser props → state via `useEffect`** : dériver pendant le rendu, ou remonter via `key` pour une divergence locale intentionnelle.
- **Error boundaries** : capturent uniquement les erreurs de rendu/cycle de vie — pas les gestionnaires d'événements, pas le code async. Ceux-ci ont besoin de leur propre `try`/`catch`.
- **`Suspense` + `React.lazy`** : permet le code splitting au niveau route/fonctionnalité — bundle initial plus petit.
- **`startTransition`** : marque une mise à jour de state comme basse priorité/interruptible pour que les mises à jour urgentes (retour de la saisie) restent réactives.
- **Tester le comportement, pas l'implémentation** : requêter par rôle/texte/label, interagir comme un utilisateur — les tests de détails d'implémentation cassent lors de refactors valides.
- **`interface` vs `type`** : interface pour les formes d'objets extensibles ; type pour les unions/intersections/mapped types.
- **Discriminated unions > soupe de booléens** : rend les combinaisons d'états invalides non représentables, et pas seulement évitées par convention.
- **`unknown` vs `any`** : `any` désactive la vérification ; `unknown` force le narrowing/la validation avant usage — toujours préférer `unknown` aux frontières de confiance.
- **Données externes** : valider à la frontière (Zod ou équivalent) — une assertion `as T` uniquement à la compilation n'impose rien à l'exécution.
- **Server state ≠ client state** : utiliser React Query/SWR pour les données fetchées (cache, revalidation) ; Context+`useReducer` ou Zustand/Redux pour le vrai client state, choisis selon l'échelle et la fréquence de mise à jour.
</content>
- **Props vs state** : les props sont des entrées en lecture seule venant du parent, le state est possédé et mis à jour via son setter ; les données descendent, les événements remontent via des props callback.
- **Handler vs effet** : action utilisateur → gestionnaire d'événement ; synchro avec un système externe → effet (avec cleanup) ; dérivable des props/state → calculer pendant le rendu. Les chaînes de callbacks d'effets ajoutent des rendus et masquent les causes.
- **React 19** : Actions (`<form action>`), `useActionState`, `useOptimistic`, `use(promise)` — le state optimiste est transitoire (attendre la mutation dans l'action) ; la promise passée à `use` doit être stable.
- **`as const` / `satisfies` / `never`** : conservent les littéraux, valident la forme sans élargir, et donnent une erreur de compilation quand un membre d'union n'est pas géré ; préférer les unions littérales à `enum`.
- **Query keys** = identité de cache + dépendances du fetch : inclure chaque entrée, structurer hiérarchiquement, invalider par préfixe après les mutations ; connaître `staleTime` (fraîcheur) vs `gcTime` (rétention du cache).
- **RSC** : bundles plus petits et data fetching colocalisé au prix d'un modèle à deux environnements, d'un verrouillage sur un framework et d'un seul `"use client"` égaré en haut qui tire tout.
- **Composants polymorphes** : generic `C extends ElementType` avec `Omit<ComponentProps<C>, keyof Own>` ; restreindre `as` pour l'accessibilité ou préférer `asChild`/des composants séparés.
- **Micro-frontends** résolvent le passage à l'échelle organisationnel, pas la performance — essayer d'abord un monorepo modulaire + feature flags ; partager React en singleton.
- **Hydration mismatch** : le premier rendu client doit égaler le HTML serveur — pas de `Date.now`/`Math.random`/`window` dans le rendu ; utiliser des effets, `useId`, ou des props venant du serveur.
- **Ne jamais définir un composant dans un composant** — un nouveau type à chaque rendu = remount, focus perdu et state perdu.
- **Mises à jour optimistes** : annuler les requêtes en vol, snapshot, rollback en cas d'erreur, invalider au settle ; désactiver les doublons et rendre les mutations idempotentes.
- **Taille de bundle** : les barrel files et packages non tree-shakables neutralisent le tree-shaking — analyser, importer granulairement, charger paresseusement les routes lourdes, imposer un budget de taille en CI.
- **Fuites mémoire dans les SPA** : listeners/souscriptions non nettoyés et tableaux en ajout seul — diff de heap snapshots, ajouter des cleanups, plafonner les collections.
