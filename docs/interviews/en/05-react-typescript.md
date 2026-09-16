# React & TypeScript

## 🟢 Fundamentals

### Q1. What are hooks, and what problem did they solve versus class components?
Hooks (`useState`, `useEffect`, etc.) let a function component hold state and trigger side
effects without being a class — before hooks, stateful logic required class components with
`this.state`/`this.setState` and lifecycle methods (`componentDidMount`,
`componentDidUpdate`, `componentWillUnmount`) spread across separate methods even when they
implemented one logical concern (subscribe in `componentDidMount`, unsubscribe in
`componentWillUnmount` — related code, split across the class). Hooks let that same concern live
together in one function, and critically, let stateful logic be extracted into reusable custom
hooks — something classes could only achieve through higher-order components or render props,
both of which added wrapper layers to the component tree ("wrapper hell").

### Q2. `useState` vs `useRef` — when do you reach for each?
`useState` triggers a re-render when its value changes, and its value is the one React renders
with on the next pass — use it for anything that should appear in the UI. `useRef` gives you a
mutable container (`.current`) that persists across renders *without* triggering a re-render
when it changes — use it for values the component needs to remember but that shouldn't drive
rendering: a DOM node reference, a timer/interval ID to clear later, or a "previous value" for
comparison. The trap: using `useRef` for something that should actually be in the UI (the value
changes but the screen never updates, since no re-render was triggered), or using `useState` for
something that doesn't need to be (causing unnecessary re-renders for a value the render output
never actually depends on).

### Q3. What's the difference between a controlled and an uncontrolled form input?
A controlled input's value is driven entirely by React state — `<input value={value}
onChange={e => setValue(e.target.value)} />` — React is the single source of truth, and every
keystroke round-trips through a state update and re-render. An uncontrolled input manages its
own internal DOM state, with React reading the current value only when needed (via a `ref`,
typically on submit) rather than on every keystroke. Controlled inputs are the default choice
because they enable real-time validation, conditional formatting, and keeping the UI in sync
with state as the user types; uncontrolled inputs avoid the per-keystroke re-render cost, which
occasionally matters for a genuinely large/complex form (see S5).

### Q4. What is JSX, and what does it actually compile to?
JSX is syntactic sugar that lets you write markup-like syntax in JavaScript;
`<div className="a">{text}</div>` compiles (via Babel or the TypeScript compiler) to a plain
function call — historically `React.createElement('div', {className: 'a'}, text)`, or with the
newer JSX transform, an automatically-imported `jsx()` call — which returns a plain JavaScript
object describing the element (type, props, children), not a DOM node. React's reconciler later
turns that object tree into actual DOM operations. Understanding this matters because it
explains why JSX has rules JavaScript syntax doesn't (a component name must be capitalized so
the compiler treats it as a variable/function reference rather than a literal HTML tag string)
and why conditional rendering is just JavaScript expressions, not special template syntax.

### Q5. TypeScript `interface` vs `type` — what's the practical difference, and when do you pick one over the other?
Both can describe an object's shape, and for that common case they're largely interchangeable.
The concrete differences: `interface` supports declaration merging (declaring the same interface
name twice merges the members — occasionally useful for extending third-party library types) and
reads slightly more naturally for extending other interfaces (`interface B extends A`); `type`
can represent things an interface can't — unions (`type Status = 'idle' | 'loading' | 'error'`),
intersections, mapped types, and conditional types. The practical rule most teams settle on:
`interface` for public object/component-prop shapes meant to be extended, `type` for unions,
utility-type compositions, and anything that isn't a plain object shape — consistency within a
codebase matters more than which specific rule is chosen.

## 🟡 Senior traps

### Q6. What is a stale closure in `useEffect`, and how does the dependency array relate to it?
**Answer:** Every render creates a new closure over that render's props/state values; an effect
function captures whichever values were in scope *when that effect instance was created*. If the
dependency array is missing a value the effect reads, the effect only gets re-created on the
renders where a *listed* dependency changes — so on other renders, it keeps running the closure
from whenever it was last created, reading that stale, captured value instead of the current
one. The fix isn't just "add every value to the array" mechanically — it's understanding that the
array controls *when the effect re-runs with fresh values*, and every value the effect body reads
generally needs to be there (or the logic restructured so it doesn't need to be, e.g. using a
functional state update `setCount(c => c + 1)` instead of reading `count` directly).

**Example:**
```jsx
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(count); // always logs 0 — this closure was created once, on mount
    }, 1000);
    return () => clearInterval(id);
  }, []); // missing `count` — the effect never re-runs to pick up a fresh closure

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

**Why it's a trap:** "just silence the `exhaustive-deps` warning, it's noisy" is the instinct
that creates this bug — the lint rule is flagging a real captured-value mismatch, not a false
positive to suppress, and suppressing it trades a visible warning for an invisible, timing-
dependent bug.

### Q7. Why does `useEffect` need a cleanup function, and what happens if you skip it for a subscription?
**Answer:** An effect can run many times over a component's life (once per dependency-array
change) and the component itself will eventually unmount — a cleanup function (the function an
effect returns) runs before the effect re-runs *and* when the component unmounts, undoing
whatever the effect set up. Skipping cleanup for something like a `setInterval`, a WebSocket
subscription, or an event listener means each effect re-run stacks up *another*
interval/subscription/listener on top of the previous ones (since nothing ever tore down the old
one), and unmounting the component leaves it running indefinitely in the background, often trying
to update state on a component that no longer exists (a classic React warning, S3) and wasting
resources for the lifetime of the page.

**Example:**
```jsx
useEffect(() => {
  const id = setInterval(() => ping(), 5000);
  return () => clearInterval(id); // omit this and every re-run/unmount stacks another interval
}, [ping]);
```

**Why it's a trap:** assuming "the component unmounted, so surely its effect stopped too" —
unmounting a component doesn't automatically undo whatever side effect its effects created; only
the returned cleanup function does that, and skipping it silently leaks timers/subscriptions for
as long as whatever it set up keeps running.

### Q8. What problem do `useMemo` and `useCallback` each solve, and what's the common misuse?
**Answer:** `useMemo` memoizes a computed *value*, recomputing only when its dependencies change
— useful when a computation is genuinely expensive (filtering/sorting a large array) and would
otherwise re-run on every render. `useCallback` memoizes a *function reference* itself, so the
same function identity is returned across renders as long as its dependencies don't change —
useful specifically when that function reference is passed to a memoized child (`React.memo`,
Q14) or used as another hook's dependency, since a new function reference every render would
otherwise defeat that memoization. The common misuse: reaching for either reflexively on every
value or callback "for performance," when for a cheap computation or a component with no
memoized children, the memoization overhead (the comparison itself, plus the memory to hold the
cached value) can cost more than the render work it was meant to save — profile before
optimizing, don't apply it as a default habit.

**Example:**
```jsx
// Reflexive memoization that doesn't help: `items` is small, filtering is cheap.
const visible = useMemo(() => items.filter(i => i.active), [items]);
// The useMemo machinery (dependency comparison, cache storage) can cost more than just
// re-running a cheap filter on every render — profile before reaching for it by default.
```

**Why it's a trap:** treating `useMemo`/`useCallback` as a default performance habit rather than
a targeted fix for a *measured* cost — over-memoizing adds real overhead (the comparison plus the
cache) for no benefit on cheap computations or components with no memoized children downstream.

### Q9. Why does React re-render, and how do keys affect reconciliation of a list?
**Answer:** A component re-renders when its own state changes, its props change, or its parent
re-renders (by default, a parent re-render cascades to re-rendering every child, regardless of
whether that child's own props actually changed, unless the child is memoized — Q14). React's
reconciler diffs the previous and new element trees to compute the minimal set of actual DOM
operations needed. For a list, `key` tells the reconciler which element in the new list
corresponds to which element in the old list across a re-render — without a stable, unique key
(or worse, using array index as a key for a list that reorders/inserts/deletes), React can
misidentify which DOM node corresponds to which logical item, causing state associated with a
list item (an input's typed value, a component's internal `useState`) to appear attached to the
wrong item after a reorder (S14).

**Example:**
```jsx
{items.map((item, index) => (
  <Row key={index} {...item} /> // index as key — breaks if items reorder/insert/delete
))}
// vs.
{items.map(item => (
  <Row key={item.id} {...item} /> // stable identity survives reordering correctly
))}
```

**Why it's a trap:** array-index keys "work" perfectly fine for a static, append-only list, which
is exactly why the bug survives code review — it only surfaces the first time the list actually
reorders or has an item removed from somewhere other than the end.

### Q10. What's the performance pitfall with React Context, and when does it become a real problem?
**Answer:** Every component that consumes a context via `useContext` re-renders whenever that
context's value changes — with no built-in way to subscribe to only part of the value, unlike a
fine-grained state management library. For a context holding a large, frequently-changing value
(especially one object recreated on every provider render, like `{ user, theme, settings }`
passed inline as `value={{ user, theme, settings }}` — a new object identity every render even
if the actual data didn't change) consumed by many components across the tree, this can trigger a
re-render storm across large portions of the UI on a single, possibly unrelated state change.
Mitigations: split context into smaller, more narrowly-scoped providers so a component only
subscribes to what it actually needs, memoize the context value object itself
(`useMemo`) so identity is stable when the underlying data hasn't changed, or move to a
selector-based state library (Redux, Zustand) for state that's both large and frequently
updated, since those support subscribing to a slice rather than the whole value.

**Example:**
```jsx
// New object identity every render, even if user/theme/settings didn't change:
<AppContext.Provider value={{ user, theme, settings }}>
// Every consumer re-renders on every parent render, regardless of which field it reads.

// Fixed: stable identity unless the underlying data actually changed.
const value = useMemo(() => ({ user, theme, settings }), [user, theme, settings]);
<AppContext.Provider value={value}>
```

**Why it's a trap:** "I'm using Context correctly, the values just come from state" misses that
the provider *itself* creates a brand-new value object every render unless memoized — Context
isn't the problem, an unmemoized wrapper object handed to it is.

### Q11. What are the Rules of Hooks, and why can't a hook be called conditionally?
**Answer:** Hooks must be called in the same order on every render, and only at the top level of
a function component or custom hook — never inside a condition, loop, or nested function. This is
because React doesn't track hooks by name; it tracks them by *call order* within a component
instance (an internal linked list matched to each render), so `useState` for "the third hook
called" only maps correctly to the same piece of state across renders if the third hook called is
always the same one. Wrapping a hook call in `if (condition) { useState(...) }` means on some
renders it's the third hook and on others it isn't the third hook at all — React has no way to
know which state belongs to which call, and the mismatch corrupts state association across every
hook after the conditional one, not just that one hook.

**Example:**
```jsx
function Profile({ showBio }) {
  if (showBio) {
    const [bio, setBio] = useState(''); // hook call order now depends on a prop
  }
  const [name, setName] = useState(''); // sometimes the 1st hook, sometimes the 2nd
  // ...
}
```

**Why it's a trap:** the code often runs without an immediate crash, especially if `showBio`
never actually flips during a given session — the corruption depends on exactly when the
condition changes across renders, which is why this is easy to introduce and hard to notice
until a specific interaction path triggers it in production.

### Q12. What's "prop drilling," and how do you decide between lifting state up versus colocating it?
**Answer:** Prop drilling is passing a value down through several layers of components that
don't themselves use it, purely so a deeply nested descendant can receive it — each intermediate
component adds an unused prop just to forward it further. The state-placement decision: keep
state as close as possible to where it's used (colocation) by default — don't lift state to a
common ancestor "just in case" something else might need it someday. Lift state up only when two
or more sibling components genuinely need to share and stay in sync with the same value. When
lifting would require drilling through many unrelated layers, that's the actual signal to reach
for Context (for infrequently-changing, broadly-needed values like theme/auth) or a state library
(for frequently-changing shared state) — not to keep drilling manually, and not to reach for
global state prematurely for something only two nearby components actually share.

**Example:**
```jsx
function Page({ user }) {                 // doesn't use `user` itself...
  return <Layout user={user} />;
}
function Layout({ user }) {                // ...neither does this...
  return <Sidebar user={user} />;
}
function Sidebar({ user }) {               // ...only this one actually needs it.
  return <span>{user.name}</span>;
}
```

**Why it's a trap:** reflexively lifting state to a common ancestor "just in case" something else
needs it someday adds this exact drilling cost for a need that may never materialize —
colocate first, and only lift once two siblings genuinely need to share the value right now.

### Q13. Why is copying a prop into local state via `useEffect` considered an anti-pattern?
**Answer:** This creates two sources of truth for the same data and a real synchronization bug:
any intervening render where `props.value` changes but the effect hasn't yet run (effects run
*after* the render commits, not during it) shows the stale `localValue`; worse, if `localValue`
is ever modified independently (e.g. local edits before a save), a subsequent prop change
silently clobbers those local edits, or a local edit gets silently overwritten by a delayed prop
update — and it's a whole extra render cycle (render with stale value, effect runs, state
updates, re-render) for something that could usually just be derived directly during render
(`const displayValue = props.value`), with no `useState`/`useEffect` needed at all. Where local
state genuinely needs to diverge from a prop intentionally (an editable form initialized from a
prop, allowed to be edited before saving), the accepted pattern is either fully uncontrolled with
a `key` prop that remounts the component when the source value changes (resetting local state
cleanly), rather than syncing via effect.

**Example:**
```jsx
// anti-pattern
const [localValue, setLocalValue] = useState(props.value);
useEffect(() => { setLocalValue(props.value); }, [props.value]);
// A prop update that lands between "render with stale localValue" and "effect runs" is
// visible to the user for one full frame, and any local edit made in that window is lost.
```

**Why it's a trap:** it looks reasonable — "keep local state synced with the prop" — but it
introduces a full extra render cycle and a real clobbering risk; the actually-correct fix
(deriving the value directly during render, or remounting via a `key` tied to the source) needs
no `useState`/`useEffect` pairing at all, which is the opposite instinct from what this pattern
reaches for.

### Q14. When does `React.memo` actually help, and why does it sometimes silently do nothing?
**Answer:** `React.memo` wraps a component so it skips re-rendering if its props are shallowly
equal to the previous render's props — it helps for a component that renders expensively (or its
subtree does) and receives the same props across most of its parent's re-renders. It silently
does nothing when a prop is a new object, array, or function created inline on every parent
render (`<Child data={{ id: 1 }} />` or `<Child onClick={() => ...} />`) — a new reference every
time means the shallow-equality check always fails, so `React.memo` compares two different
objects that happen to have equal contents and (correctly, per its default shallow comparison)
decides they're different, re-rendering every time regardless. The fix is memoizing whatever's
passed as a prop with `useMemo`/`useCallback` (Q8) at the point it's created, not just wrapping
the receiving child — memoizing only one side of that relationship does nothing.

**Example:**
```jsx
const Row = React.memo(function Row({ onSelect }) { /* ... */ });

function List({ items }) {
  return items.map(item => (
    <Row key={item.id} onSelect={() => select(item.id)} /> // new function every render
  ));
}
// React.memo's shallow prop comparison sees a different `onSelect` reference every time —
// it re-renders every Row on every List render regardless of memoization.
```

**Why it's a trap:** wrapping the child in `React.memo` feels like "I did the performance work,"
but memoizing only one side of the parent/child relationship does nothing if the parent keeps
creating new prop references — both sides need to cooperate for the memoization to hold.

### Q15. Give a practical use case for TypeScript generics in a React codebase.
**Answer:** A typed data-fetching hook is the canonical example: `function useApi<T>(url: string):
{ data: T | null; loading: boolean; error: Error | null }` lets every call site get full type
inference for its own specific response shape (`useApi<User>('/api/user')` gives `data` the type
`User | null`) without writing a separate hook per endpoint or losing type safety with a generic
`any`-typed fetch wrapper. Generic components follow the same idea — a reusable `<Select<T>>` or
`<List<T>>` component that's typed to whatever item type it's given, so consumers get correct
autocomplete and type-checking on `onSelect: (item: T) => void` regardless of what `T` ends up
being at each call site, without the component needing to know in advance every type it might
ever render.

**Example:**
```tsx
function useApi<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(url).then(r => r.json()).then((d: T) => { setData(d); setLoading(false); });
  }, [url]);
  return { data, loading };
}

const { data } = useApi<User>('/api/user'); // data: User | null, fully inferred
```

**Why it's a trap:** writing this hook with `any` instead of a generic type parameter "works" the
same way at every call site until a caller destructures a field that doesn't exist — the generic
version catches that mismatch at compile time; `any` catches nothing at all.

### Q16. Why prefer a discriminated union over several boolean flags for modeling request state?
**Answer:** With separate booleans (`isLoading`, `isError`, `data`, `error`), the type system
allows impossible combinations (`isLoading: true, isError: true` simultaneously, or `data`
present while `isLoading` is also true) — nothing prevents that invalid state from being
constructed, and every consumer has to defensively guard against combinations that shouldn't
happen but technically can. A discriminated union makes invalid states genuinely
unrepresentable: you can only be in exactly one of the listed shapes at a time, and narrowing on
`status` in a `switch` gives you type-safe access to `data` only in the `success` branch and
`error` only in the `error` branch — the compiler enforces the state machine's actual valid
transitions instead of the code needing to enforce it manually everywhere the state is read.

**Example:**
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

**Why it's a trap:** modeling request state as several independent booleans feels natural — each
new state seems to need just one more flag — but nothing stops those flags from being set in
combinations that should be impossible, and every consumer ends up defensively guarding against
states the type system should have ruled out entirely.

### Q17. Why is `unknown` considered safer than `any` in TypeScript?
**Answer:** `any` opts a value out of type checking entirely — you can call any method, access
any property, pass it anywhere, and the compiler allows all of it with no error, even nonsensical
operations, silently reintroducing exactly the class of runtime type error TypeScript exists to
catch. `unknown` also accepts any value assigned to it, but the compiler *refuses* to let you do
anything with it (call a method, access a property, pass it to a typed parameter) until you've
narrowed its type first — via a type guard, `typeof`/`instanceof` check, or an explicit
assertion. This makes `unknown` the correct type for something genuinely unknown at the boundary
(a parsed JSON payload, an external API response, a `catch` block's error) — it forces the
narrowing/validation step (S16's scenario) rather than letting an unchecked value silently flow
through the rest of the codebase as if it were fully trusted.

**Example:**
```ts
function handle(x: any) { x.toUpperCase(); }   // compiles — crashes at runtime if x isn't a string
function handleSafe(x: unknown) {
  if (typeof x === 'string') x.toUpperCase();  // compiler forces this check first
}
```

**Why it's a trap:** `any` "feels" like a normal type because TypeScript never complains about
it — that silence is exactly the danger; `unknown` carries the same lack of upfront type
information but forces the narrowing step before any operation is allowed to compile at all.

### Q18. When does `useReducer` fit better than `useState`?
**Answer:** `useReducer` earns its structure when state updates involve multiple related
sub-values that change together (so a single dispatched action can update several fields
atomically and consistently, instead of several separate `setState` calls that could get out of
sync if one is forgotten), when the next state genuinely depends on complex logic based on the
previous state and the action (not just "replace with this new value"), or when the same
state-transition logic needs to be triggered from many different places (centralizing it as named
actions in one reducer function is easier to reason about, and to test in isolation, than the
same logic duplicated across several `onClick` handlers each calling multiple `setState`s). For
simple, independent pieces of state, `useState` remains simpler and more direct — reaching for
`useReducer` reflexively for a single boolean toggle is unnecessary ceremony.

**Example:**
```jsx
// Several setState calls that can drift out of sync if one call site forgets one:
setLoading(true); setError(null); setData(null);

// One dispatched action keeps them atomic and consistent by construction:
dispatch({ type: 'FETCH_START' });
```

**Why it's a trap:** reaching for `useReducer` for a single independent boolean is unnecessary
ceremony — the real signal is "do these fields change together as one logical transition," not
simply "is there more than one piece of state."

### Q19. What is `Suspense`, and how does it enable code splitting?
**Answer:** `Suspense` lets a component tree "wait" for something (most commonly a lazily-loaded
component module, via `React.lazy(() => import('./HeavyComponent'))`) and render a fallback UI in
the meantime, without the loading logic being manually threaded through as a boolean state and
conditional render. Combined with `React.lazy`, this is the mechanism behind code splitting: the
lazily-imported component's code isn't included in the initial JavaScript bundle at all — it's
fetched as a separate chunk only when that part of the tree is actually rendered — which reduces
initial bundle size and load time for routes/features a given user session may never visit,
letting `Suspense` show a spinner or skeleton for the brief window while that chunk downloads.

**Example:**
```jsx
const HeavyEditor = React.lazy(() => import('./HeavyEditor'));

function Page() {
  return (
    <Suspense fallback={<Spinner />}>
      <HeavyEditor />
    </Suspense>
  );
}
// HeavyEditor's code is a separate chunk, fetched only when this tree actually renders it.
```

**Why it's a trap:** wrapping something in `Suspense` without actually code-splitting it via
`React.lazy`/dynamic `import()` accomplishes nothing on its own — `Suspense` only creates a
waiting boundary; the bundle-size win comes entirely from the lazy import, not from the boundary
itself.

### Q20. What do React error boundaries actually catch, and what do they explicitly not catch?
**Answer:** An error boundary (a class component implementing `static getDerivedStateFromError`
and/or `componentDidCatch`, since there's no hook equivalent) catches errors thrown during
rendering, in lifecycle methods, and in constructors of the component tree below it, replacing
that subtree with a fallback UI instead of crashing the whole app. It explicitly does **not**
catch errors inside event handlers (a `try`/`catch` in the handler itself is the right tool
there, since an event handler firing after a successful render isn't part of React's render
process), asynchronous code (a `.then()`/`await` inside a `useEffect`, a `setTimeout` callback —
same reasoning, it runs outside the render phase the boundary wraps), errors during server-side
rendering, or errors thrown in the error boundary's own fallback rendering code.

**Example:**
```jsx
class ErrorBoundary extends React.Component {
  static getDerivedStateFromError(error) { return { hasError: true }; }
  render() { return this.state.hasError ? <Fallback /> : this.props.children; }
}

function Button() {
  const onClick = () => { throw new Error('boom'); }; // NOT caught by any ErrorBoundary above
  return <button onClick={onClick}>Click</button>;
}
```

**Why it's a trap:** assuming an error boundary wrapping the whole app is a safety net for *any*
uncaught error — event handlers and async callbacks run outside the render phase the boundary
observes, so they need their own `try`/`catch` regardless of how high up the tree a boundary
sits.

### Q21. What problem does `startTransition` / concurrent rendering solve?
**Answer:** Without it, a state update that triggers an expensive re-render (filtering a large
list as the user types in a search box) blocks the browser's main thread until that render
completes, including blocking the very keystroke-driven state update (updating the input's own
displayed value) that triggered it — the input feels laggy because rendering the expensive part
and rendering the input's own immediate feedback are treated with equal, synchronous urgency.
`startTransition` lets you mark a state update as non-urgent ("this can be interrupted and
finished a bit later"), so React can prioritize the urgent update (the input reflecting what was
just typed) and defer/interrupt the expensive one, keeping the UI responsive to input even while
a large re-render is still catching up in the background.

**Example:**
```jsx
function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  function onChange(e) {
    setQuery(e.target.value);                            // urgent — keep the input responsive
    startTransition(() => {
      setResults(filterBigList(e.target.value));          // non-urgent — can be interrupted
    });
  }
}
```

**Why it's a trap:** wrapping the *input's own* state update in `startTransition` instead of the
expensive derived one defeats the point entirely — the input's own update must stay in the
urgent lane; only the expensive, non-critical update should be deferred.

### Q22. What should you actually test in a React component, per the React Testing Library philosophy?
**Answer:** Test behavior as a user would experience it — render the component, interact with it
the way a user would (click, type, find elements by visible text/role/label, not by CSS class or
internal implementation), and assert on what's visible or triggered as a result — rather than
testing internal implementation details like a component's specific state values, which hooks it
calls internally, or its exact render tree shape. The underlying reasoning: implementation-detail
tests break on a valid refactor that doesn't change user-facing behavior at all (renaming an
internal state variable, switching from `useState` to `useReducer` internally), which trains the
team to distrust or ignore failing tests — a test suite should fail when behavior actually
breaks, and stay green through internal restructuring that doesn't change what the user sees or
can do.

**Example:**
```jsx
// Implementation-detail test — breaks on a valid internal refactor.
expect(wrapper.state('isOpen')).toBe(true);

// Behavior test — survives the same refactor.
expect(screen.getByRole('dialog')).toBeVisible();
```

**Why it's a trap:** implementation-detail tests pass just as easily as behavior tests when
everything's fine, so the difference is invisible until the first valid refactor breaks a wall of
tests that shouldn't have cared — trust erodes, and teams start ignoring red CI, which is worse
than not having the tests at all.

## 🔴 Expert / Open

### Q23. A large data table becomes noticeably janky when scrolling or filtering. Walk through diagnosing and fixing it.
Start with the React DevTools Profiler to see what's actually re-rendering and how long it takes
— don't guess. Common findings, roughly in order of likelihood: every row re-renders on every
keystroke of a filter input because the row components aren't memoized (`React.memo`) or because
they are memoized but receive a new inline function/object prop every render (Q14's trap) so the
memoization does nothing; the entire (large) dataset is rendered to the DOM at once rather than
only the visible rows, so scroll performance is bounded by total row count, not visible row
count — the fix here is list virtualization (rendering only the rows currently in or near the
viewport, e.g. `react-window`/`react-virtual`), which is the single highest-impact fix for a
genuinely large list, since it makes render cost independent of total item count; and an
expensive computation (sorting, filtering, aggregating) re-running on every render rather than
being memoized with `useMemo` keyed on the actual inputs that affect it. The senior-level
distinction: profile first, fix the specific bottleneck the profiler actually shows, rather than
reflexively wrapping everything in `memo`/`useMemo` — over-memoization has its own cost (Q8) and
doesn't help if virtualization was the real fix needed.

### Q24. Design a typed API client / data-fetching layer using TypeScript generics, with proper error handling.
A generic request function typed on the expected response shape (`function apiRequest<T>(url:
string, schema: ZodSchema<T>): Promise<T>`) that performs the fetch, checks the HTTP status
explicitly (a non-2xx response is not automatically a JavaScript exception — `fetch` only rejects
on network failure, not on 404/500), and — critically for real type safety, not just declared
type safety — validates the parsed JSON against a runtime schema (Zod, or similar) before
returning it typed as `T`, rather than simply asserting `as T` on unchecked JSON (Q17's
`unknown`-vs-`any` point applies directly here: an external response is `unknown` until it's
actually been checked, and `as T` on unvalidated `unknown` is a compile-time-only promise the
runtime doesn't enforce, which is exactly how S16 happens). Errors are modeled as a discriminated
union result (Q16) rather than thrown exceptions for expected failure modes (a validation error,
a 404, a network failure each get their own typed variant), so callers are compiler-forced to
handle each case explicitly via the `status` narrowing, rather than an easily-forgotten
`try`/`catch` around a thrown error. Each specific endpoint then becomes a thin, fully-typed
wrapper: `getUser(id: string) { return apiRequest(`/users/${id}`, userSchema); }`.

### Q25. How do you decide between Context + `useReducer`, and a dedicated state library (Redux, Zustand, React Query)?
Start from what kind of state is actually being managed, since "which library" is the wrong first
question. **Server state** (data fetched from an API, with caching, revalidation, background
refetching, and loading/error states as first-class concerns) is a fundamentally different
problem from client state, and a purpose-built tool (React Query/TanStack Query, SWR) solves it
far more completely than hand-rolling it with Context — this is usually the single highest-value
library adoption for a typical CRUD app, independent of the client-state answer. For genuine
**client state** (UI state, user preferences, anything not mirroring server data): Context +
`useReducer` is sufficient and adds no dependency when the state is small, changes infrequently,
and doesn't have the performance profile that triggers Q10's re-render problem across a large
consumer tree. Reach for a dedicated client-state library (Zustand, Redux) specifically when
state is large and frequently updated with many consumers needing only slices of it (avoiding
Q10's all-consumers-re-render problem via selectors), when the team needs strong dev tooling
(time-travel debugging, well-established middleware patterns) for a genuinely complex state
machine, or when the same state needs to be read/written from many unrelated parts of a large
codebase in a way that ad-hoc Context composition becomes hard to reason about. The
interview-worthy answer names the actual constraint driving the choice, not a library preference
stated as if it were a universal default.

## 🎯 Real-world scenarios

### S1. A component enters an infinite re-render loop, freezing the tab
- **Symptoms:** The browser tab becomes unresponsive, React DevTools (if it loads at all) shows
  an endlessly incrementing render count, and the console may show a "Maximum update depth
  exceeded" error.
- **Diagnosis:** Look for a `setState` call directly in the render body (outside an event handler
  or effect) — that triggers a re-render, which calls the render body again, which calls
  `setState` again — or a `useEffect` with a dependency array that includes a value the effect
  itself updates without any guard, so each run's update triggers the next run.
- **Example:**
  ```jsx
  function Broken() {
    const [count, setCount] = useState(0);
    setCount(count + 1); // called directly in the render body — not in an effect/handler
    return <div>{count}</div>;
  }
  // Render calls setCount -> triggers a re-render -> calls setCount again -> ... forever.
  ```
- **Resolution:** Move the `setState` call into an event handler, or into an effect with a
  dependency array that correctly reflects only what should trigger it, adding a guard condition
  if the update should only happen once or under specific conditions rather than every time the
  effect's dependencies happen to be re-evaluated as equal.
- **Prevention:** React's "Maximum update depth exceeded" error and the ESLint
  `react-hooks/exhaustive-deps` rule both exist specifically to catch this class of bug early —
  keep that lint rule enabled rather than suppressing it to silence a warning without
  understanding it.

### S2. A counter displayed via `setInterval` inside `useEffect` always shows the same value, never incrementing
- **Symptoms:** A component sets up `setInterval` in a `useEffect` to log or display a state
  value periodically, but the value shown never changes from what it was on the very first
  render, even though the actual state elsewhere in the app has since updated.
- **Diagnosis:** Classic stale closure (Q6) — the effect's `[]` (empty) dependency array means the
  interval callback was created exactly once, closing over whatever `count` was on that first
  render, and since the effect never re-runs, that closure (and its captured `count`) never
  updates either.
- **Example:**
  ```jsx
  useEffect(() => {
    const id = setInterval(() => setCount(count + 1), 1000); // reads `count` from this closure
    return () => clearInterval(id);
  }, []); // count never appears here, so this closure — and its `count` — never refreshes
  ```
- **Resolution:** Either add `count` to the dependency array (accepting that the interval gets
  torn down and recreated every time `count` changes, which is often fine), or — the more robust
  fix for this specific pattern — use a functional state update (`setCount(c => c + 1)`) inside
  the interval, which doesn't need to read the current `count` from the closure at all, so the
  effect's dependency array can correctly stay `[]`.
- **Prevention:** Treat `react-hooks/exhaustive-deps` warnings as bugs to fix, not noise to
  suppress with an eslint-disable comment — the lint rule is specifically designed to catch this
  exact stale-closure pattern before it ships.

### S3. The console repeatedly logs "Can't perform a React state update on an unmounted component"
- **Symptoms:** This warning appears, usually after navigating away from a page quickly, or when
  a slow network response returns after the user has already moved on.
- **Diagnosis:** An async operation (a fetch, a subscription callback) was started while the
  component was mounted, and its `.then()`/callback calls `setState` after the component has
  since unmounted — the async operation doesn't know or care that its component is gone by the
  time it resolves.
- **Example:**
  ```
  Warning: Can't perform a React state update on an unmounted component. This is a no-op,
  but it indicates a memory leak in your application. To fix, cancel all subscriptions and
  asynchronous tasks in a useEffect cleanup function.
      at UserProfile (UserProfile.jsx:14)
  ```
- **Resolution:** Use an `AbortController` to actually cancel the in-flight fetch on unmount (via
  the effect's cleanup function), or, if cancellation isn't available for the specific async
  source, track a mounted flag/ref and check it before calling `setState` in the callback.
- **Prevention:** Every effect that starts an async operation should have a cleanup function that
  addresses what happens if that operation resolves after unmount — this should be a standard
  part of writing any data-fetching effect, not something added reactively after the warning
  appears.

### S4. A large table becomes visibly janky (dropped frames, laggy scrolling) once it has a few thousand rows
- **Symptoms:** Scroll performance is smooth with a small dataset but degrades sharply as row
  count grows into the thousands, well before the data itself would be considered "large" by
  backend standards.
- **Diagnosis:** Confirmed with the Profiler (Q23) — the entire dataset is being rendered to
  actual DOM nodes at once, so both initial render and any scroll-triggered work scale with total
  row count rather than visible row count.
- **Example:**
  ```
  # React DevTools Profiler flame graph: every <Row> commits on every filter keystroke,
  # including rows whose data didn't change — 4,000 committed Row renders per keystroke,
  # even though only ~20 rows are ever visible in the viewport at once.
  ```
- **Resolution:** Introduce list virtualization (`react-window` or `react-virtual`), rendering
  only the rows within or near the current viewport and recycling DOM nodes as the user scrolls,
  which makes render cost roughly constant regardless of total dataset size.
- **Prevention:** Set an explicit row-count threshold in code review/design above which any new
  list or table component is expected to be virtualized from the start, rather than discovered as
  a performance bug once real data volume arrives in production.

### S5. Typing in a text input feels laggy, with visible delay between a keystroke and the character appearing
- **Symptoms:** A controlled input's perceived responsiveness degrades noticeably, especially in
  a form embedded within a larger, complex page.
- **Diagnosis:** Check what else re-renders as a side effect of the input's `onChange` — the
  input's own `setState` call is cheap, but if that state lives on (or triggers a re-render of) a
  large parent component whose subtree isn't memoized, every keystroke triggers a full expensive
  re-render of that whole subtree before the character visually appears, since React's default
  render behavior is synchronous.
- **Example:**
  ```jsx
  function Page() {
    const [text, setText] = useState('');
    return (
      <>
        <input value={text} onChange={e => setText(e.target.value)} />
        <ExpensiveChart data={text} /> {/* re-renders synchronously on every keystroke */}
      </>
    );
  }
  ```
- **Resolution:** Move the input's own state as local as possible (colocation, Q12) so its
  `setState` only re-renders the input itself and its immediate surroundings, not the whole page;
  memoize expensive sibling/parent subtrees so they don't re-render just because unrelated local
  state changed; for genuinely expensive downstream work driven by the input's value (e.g.
  filtering a large list as the user types), debounce that work or wrap it in `startTransition`
  (Q21) so it doesn't block the input's own immediate visual feedback.
- **Prevention:** Keep form input state colocated with the input by default, and treat any
  "typing feels laggy" report as a state-placement/memoization question to profile immediately,
  rather than something to work around with throttling alone.

### S6. Changing a small piece of app-wide state (e.g. toggling dark mode) causes a noticeable, visible re-render across the entire page
- **Symptoms:** A single global setting change (theme, language, feature flag) causes a visible
  flash/re-render across large parts of the UI that have nothing to do with that setting.
- **Diagnosis:** All that state lives in one shared Context whose consumers span most of the
  component tree, and Context's all-consumers-re-render-on-any-change behavior (Q10) means a
  single Context value change re-renders every consumer, regardless of whether a given consumer
  actually cares about the specific field that changed.
- **Example:**
  ```jsx
  <AppContext.Provider value={{ theme, user, flags }}> {/* new object every render */}
    <App /> {/* every consumer anywhere in the tree re-renders on any single field change */}
  </AppContext.Provider>
  ```
- **Resolution:** Split the single large context into several narrower contexts (a `ThemeContext`
  separate from a `UserContext`, separate from a `FeatureFlagsContext`) so a theme change only
  re-renders theme consumers, not user-data consumers; memoize the context's value object with
  `useMemo` if it's being recreated inline on every provider render regardless of whether the
  underlying data changed.
- **Prevention:** Avoid a single "app state" context holding many unrelated concerns bundled
  together — design context boundaries around what actually needs to change together, from the
  start, rather than consolidating for convenience and splitting later once the re-render cost
  becomes visible.

### S7. The app crashes in production with a runtime type error, despite the TypeScript build passing cleanly
- **Symptoms:** `TypeScript compiled with 0 errors`, yet a production error-tracking tool shows a
  `TypeError: cannot read property 'x' of undefined` on a value the type system claimed was
  always present.
- **Diagnosis:** Search the surrounding code for `as` type assertions or `any` — a common root
  cause is data from an external boundary (an API response, `localStorage`, a third-party
  library without types) being force-cast (`as User`) rather than validated, so TypeScript
  trusted the assertion at compile time with no runtime check ever confirming the actual shape
  matched.
- **Example:**
  ```ts
  const user = JSON.parse(response) as User; // compiler trusts this unconditionally
  user.email.toLowerCase(); // TypeError: Cannot read properties of undefined — API omitted `email`
  ```
- **Resolution:** Replace the unchecked assertion with runtime validation at the boundary (a
  schema library like Zod, or at minimum explicit shape checks) so a mismatched response fails
  loudly and specifically at the boundary, rather than propagating an incorrectly-typed value
  deep into the app until it crashes somewhere unrelated.
- **Prevention:** Treat any `as SomeType` on data originating outside the codebase's own control
  as a code-review flag requiring justification — `unknown` plus explicit validation (Q17, Q24)
  should be the default pattern for any external data boundary, not an occasional hardening
  measure.

### S8. Search results occasionally show results for a previous, already-abandoned search query
- **Symptoms:** Typing quickly in a search box sometimes results in the displayed results
  reverting to (or flickering to) results for an earlier, shorter query, even though the input
  itself shows the latest typed text.
- **Diagnosis:** A race condition between out-of-order network responses — each keystroke fires a
  new fetch, but network responses aren't guaranteed to resolve in the order they were sent; if
  the effect naively does `fetch(query).then(setResults)` for every keystroke with no
  cancellation or ordering check, a slower response for an earlier query can resolve *after* a
  faster response for the latest query, overwriting the correct, more recent results with stale
  ones.
- **Example:**
  ```jsx
  useEffect(() => {
    fetch(`/search?q=${query}`).then(r => r.json()).then(setResults);
    // no cancellation — a slow response for an earlier, shorter query can resolve after
    // a faster response for the latest query, overwriting it with stale results
  }, [query]);
  ```
- **Resolution:** Use `AbortController` to cancel the previous request when a new one starts
  (the effect's cleanup function aborting the prior fetch, same mechanism as S3), or track which
  query the most recent response corresponds to and ignore/discard any response that doesn't
  match the current query by the time it resolves.
- **Prevention:** Any effect that fetches based on a rapidly-changing input (search-as-you-type,
  rapid filter changes) needs explicit handling for out-of-order responses from the start — this
  is common enough that many data-fetching libraries (React Query included) handle it
  automatically, which is itself a reason to prefer them over hand-rolled fetch effects for this
  exact pattern.

### S9. An API endpoint is called twice for what should be a single component mount
- **Symptoms:** Network tab shows the same GET request firing twice in quick succession when a
  component first renders, in development specifically (and the team is confused whether this
  also happens in production).
- **Diagnosis:** In development, React's `StrictMode` deliberately double-invokes certain
  lifecycle-equivalent behavior (mounting, unmounting, and re-mounting a component, and thus
  re-running effects) specifically to help surface effects that aren't properly cleaned up — this
  is intentional, development-only behavior, not a production bug, *if* the effect's cleanup
  function correctly cancels/undoes the first invocation's work. If it also happens in
  production, the actual cause is more likely a missing or incorrect dependency array causing a
  genuine duplicate effect run outside of `StrictMode`'s deliberate double-invoke.
- **Example:**
  ```
  # Network tab in development:
  GET /api/user   200   (fired at mount)
  GET /api/user   200   (fired again, ~0ms later — StrictMode's deliberate double-invoke)
  ```
- **Resolution:** For the `StrictMode` case, this usually indicates the effect's side effect
  (the fetch) doesn't have a cleanup step and doesn't need one to be "correct" per se, but it's
  worth confirming the duplicate call is genuinely harmless (idempotent, not causing a duplicate
  write) — for a mutating effect, this is exactly the case where correct cleanup (cancelling the
  first fetch) matters. For a genuine production duplicate, fix the dependency array or add a
  guard against a duplicate in-flight request for the same query.
- **Prevention:** Don't disable `StrictMode` to make the symptom go away — treat it as the
  intended signal to verify effect cleanup is correct, since the underlying bug it's surfacing
  (an effect without proper cleanup) is a real latent issue even if it doesn't visibly duplicate a
  call in production today.

### S10. A refactor to pass a new value through five layers of components becomes a large, error-prone diff
- **Symptoms:** Adding one new piece of data that a deeply nested component needs requires
  touching every intermediate component's props interface along the path to it, for data those
  intermediate components don't otherwise use.
- **Diagnosis:** This is prop drilling (Q12) reaching the point where it's actively costly — the
  component tree's structure doesn't match the data's actual scope of relevance, and every future
  change to this value repeats the same wide, brittle diff.
- **Example:**
  ```jsx
  // Adding `locale` means touching every layer along the path, even ones that never use it:
  <Page locale={locale}>
    <Layout locale={locale}>
      <Sidebar locale={locale}>
        <Widget locale={locale} />
      </Sidebar>
    </Layout>
  </Page>
  ```
- **Resolution:** For genuinely broadly-needed, infrequently-changing data (current user, theme,
  locale), introduce a Context at an appropriate ancestor so only the components that actually
  need the value consume it directly, bypassing the intermediate layers entirely; for frequently-
  changing or large shared state, this is the point to evaluate a dedicated state library (Q25)
  instead of solving it with Context alone.
- **Prevention:** Treat "does this value need to pass through components that don't use it" as a
  design question when a data dependency is first introduced, not just when the drilling has
  already spread across five layers and refactoring becomes expensive.

### S11. An error thrown inside a button's `onClick` handler crashes the whole page instead of being caught by the app's error boundary
- **Symptoms:** The team added an error boundary wrapping the app specifically to prevent a
  full-page crash on unexpected errors, but a bug in an `onClick` handler still produces a blank
  white screen (or an unhandled console error) instead of the expected fallback UI.
- **Diagnosis:** Error boundaries don't catch event handler errors by design (Q20) — the handler
  runs outside React's render phase, after a successful render, so it's simply not something the
  boundary's `componentDidCatch` mechanism observes.
- **Example:**
  ```jsx
  <ErrorBoundary>
    <button onClick={() => { throw new Error('boom'); }}>Click</button>
  </ErrorBoundary>
  // The boundary never sees this — it only wraps render/lifecycle, not event handlers.
  ```
- **Resolution:** Add explicit `try`/`catch` inside the event handler itself (or the function it
  calls) for anything that can realistically throw, handling the error locally (showing an inline
  message, logging it) rather than expecting the boundary to catch it.
- **Prevention:** Document clearly (in team conventions, not just tribal knowledge) that error
  boundaries only cover the render/lifecycle path, and that event handlers and async code need
  their own explicit error handling — this is a genuinely common misunderstanding worth calling
  out directly during onboarding or code review the first time it comes up.

### S12. Initial page load time is slow, and the network tab shows a very large single JavaScript bundle
- **Symptoms:** Time-to-interactive is high even on a fast connection, and the bundle analyzer
  shows one large `main.js` containing code for routes/features most users on this initial page
  never visit.
- **Diagnosis:** No code splitting is in place — every route and feature, including rarely-used
  ones (an admin panel, a settings page, a rarely-opened modal's heavy dependency), is bundled
  into the initial load regardless of whether the current page needs it.
- **Example:**
  ```
  $ npx source-map-explorer build/static/js/main.*.js
  # main.js: 3.8 MB — includes the admin panel, the rich-text editor, and a charting
  # library, none of which the landing page (the most-visited route) ever renders.
  ```
- **Resolution:** Introduce route-level code splitting with `React.lazy` and `Suspense` (Q19) at
  minimum, so each route's code is a separate chunk fetched only when navigated to; for
  particularly heavy individual features within a route (a rich text editor, a charting library),
  split those out too and lazy-load them on interaction (e.g. only when a specific tab is opened)
  rather than bundling them with the route that merely contains the option to open them.
- **Prevention:** Run a bundle analyzer as part of the regular build/review process (not just
  once, retroactively) so a large new dependency being added to the initial bundle is caught at
  the PR that introduces it.

### S13. A refactor that doesn't change any user-facing behavior breaks a large fraction of the test suite
- **Symptoms:** Renaming an internal state variable, converting a component from `useState` to
  `useReducer` internally, or restructuring how a component is composed internally — none of
  which change what the user sees or can do — causes many tests to fail.
- **Diagnosis:** The test suite is asserting on implementation details (internal state shape,
  specific internal method calls, shallow-rendered component tree structure) rather than
  user-observable behavior — the anti-pattern Q22 describes, often from testing utilities/patterns
  that encourage reaching into a component's internals rather than interacting with it the way a
  user would.
- **Example:**
  ```jsx
  // Breaks on a valid internal refactor from useState to useReducer:
  expect(wrapper.instance().state.isOpen).toBe(true);

  // Survives the same refactor:
  expect(screen.getByRole('dialog')).toBeVisible();
  ```
- **Resolution:** Rewrite the brittle tests to interact with the rendered output the way a user
  would (find by role/text/label, click, type, assert on what's visible), which should then
  survive the internal refactor unchanged since the user-facing behavior genuinely didn't change.
- **Prevention:** Adopt Testing Library's query priorities (prefer `getByRole`/`getByLabelText`
  over `getByTestId`, and strongly prefer either over reaching into component internals) as a
  team convention from the start, and treat "does this test still pass after a valid,
  behavior-preserving refactor" as the actual bar for a good test, not "does it pass right now."

### S14. Items in a reorderable list occasionally show the wrong content, or lose their local input state, after being reordered
- **Symptoms:** A drag-to-reorder list, or a list where items can be inserted/removed from the
  middle, shows a mismatch after reordering — an item's checkbox state, or an input's typed
  value, appears attached to the wrong row after the reorder.
- **Diagnosis:** Check the `key` prop used for the list — this is the classic symptom of using
  array index as `key` for a list that reorders: React matches DOM nodes (and their internal
  state) to list positions by key across a re-render, and if the key is the index rather than a
  stable per-item identifier, reordering the underlying data doesn't actually reorder which DOM
  node/state React associates with which item — it just changes what data renders at each
  existing index, leaving any local per-item state behind at the old position.
- **Example:**
  ```jsx
  {todos.map((todo, i) => (
    <TodoRow key={i} todo={todo} /> // reordering `todos` doesn't reorder which DOM node/state
  ))}                                // React associates with which item — it just re-renders
                                     // the same node index with different data
  ```
- **Resolution:** Use a stable, unique identifier from the actual data (a database ID, a UUID) as
  the `key`, not the array index, so React correctly tracks which rendered instance corresponds
  to which logical item across reorders, insertions, and deletions.
- **Prevention:** Treat "array index as key" as a lint-flagged anti-pattern for any list that can
  reorder, filter, or have items inserted/removed from anywhere but the end — it's a fine,
  harmless choice only for a genuinely static, append-only, never-reordered list, and that
  exception is narrow enough that defaulting to a real ID is the safer habit regardless.

### S15. A component's displayed value silently drifts out of sync with the prop it was supposed to reflect
- **Symptoms:** A component that copies an incoming prop into local state (to allow local editing
  before save) sometimes shows stale data after the prop updates elsewhere, or loses a user's
  in-progress local edit when the prop happens to update for an unrelated reason.
- **Diagnosis:** This is exactly Q13's anti-pattern — syncing a prop into state via `useEffect`
  creates two sources of truth, and the effect-based sync introduces a render-cycle gap (and a
  clobbering risk) between the prop's actual current value and the local state mirroring it.
- **Example:**
  ```jsx
  const [draft, setDraft] = useState(props.value);
  useEffect(() => { setDraft(props.value); }, [props.value]);
  // A prop update landing between "the user starts editing" and "the effect runs" can
  // silently clobber their in-progress edit, or briefly show the old value on-screen.
  ```
- **Resolution:** If the component doesn't actually need to diverge from the prop (just displays
  it), remove the local state/effect pair entirely and derive the displayed value directly from
  the prop during render. If local divergence is genuinely needed (an editable draft), use a
  `key` prop on the component tied to whatever identifies "a new source value" (e.g. the entity's
  ID) so React remounts the component with fresh local state exactly when the source changes,
  rather than trying to reconcile old local state against a new prop via an effect.
- **Prevention:** Treat "local state initialized from a prop, kept in sync via `useEffect`" as a
  design smell to question immediately in review — it's rarely the simplest correct solution to
  whatever problem prompted it, and the `key`-remount pattern or plain derivation almost always
  replaces it more simply and correctly.

### S16. The TypeScript build is clean, but the app crashes when parsing a third-party API's response
- **Symptoms:** A recently integrated external API occasionally returns a field as `null` where
  the TypeScript interface declares it as a required `string`, and the app crashes trying to call
  a string method on it — the compiler never flagged this because it has no way to verify an
  external HTTP response actually matches a hand-written interface.
- **Diagnosis:** The interface describing the API response was written by hand (or generated once
  from a sample response) and asserted onto the parsed JSON, rather than validated — TypeScript
  types are erased at compile time (module 1, Q13's erasure point applies analogously here) and
  provide zero runtime enforcement; a mismatch between the declared type and the actual response
  shape is invisible to the compiler and only manifests when the mismatched data is actually used.
- **Example:**
  ```ts
  interface ApiUser { id: string; email: string; } // hand-written, never actually verified
  const user = (await res.json()) as ApiUser;
  user.email.toLowerCase(); // API returns `email: null` for unverified accounts — crashes here
  ```
- **Resolution:** Add runtime schema validation (Zod, or equivalent) at the point the response is
  parsed, so a shape mismatch is caught immediately with a clear error identifying exactly which
  field didn't match, instead of manifesting later as an unrelated-looking crash deep in the
  component tree; decide explicitly (and type accordingly, e.g. `string | null`) how the field
  should actually be treated once its real nullability is known.
- **Prevention:** Any data crossing a trust boundary from outside the codebase's own control (a
  third-party API, in particular one the team doesn't control the contract of) should be treated
  as `unknown` and validated at the boundary by default (Q17, Q24) — a hand-written interface with
  no runtime check is a promise the compiler makes on the codebase's behalf that it has no actual
  ability to keep.

## 📌 Cheat-sheet

- **Hooks**: same stateful-logic-together benefit classes couldn't give without wrapper hell; must be called unconditionally, same order every render.
- **`useState` vs `useRef`**: state triggers re-render and drives UI; ref persists mutably without triggering one — use for DOM nodes, timers, non-UI values.
- **Stale closures**: an effect's captured values are frozen at creation time; `[]` deps + reading a changing value = bug. Prefer functional updates (`setX(x => ...)`) to sidestep it.
- **Effect cleanup**: required for anything that persists beyond one run — subscriptions, intervals, listeners, in-flight fetches (`AbortController`).
- **`useMemo`/`useCallback`**: memoize expensive computations / stable function identity for memoized children — profile before applying, don't default to it everywhere.
- **`React.memo`**: shallow prop comparison; useless if the parent passes new inline objects/functions every render — memoize at the source, not just the receiver.
- **`key`**: stable per-item ID, never array index for a reorderable/mutable list — wrong key = state/content attached to the wrong row.
- **Context**: all consumers re-render on any value change — split into narrow contexts and memoize the value object for frequently-updated, widely-consumed state.
- **Don't sync props → state via `useEffect`**: derive during render, or remount via `key` for intentional local divergence.
- **Error boundaries**: catch render/lifecycle errors only — not event handlers, not async code. Those need their own `try`/`catch`.
- **`Suspense` + `React.lazy`**: enables route/feature-level code splitting — smaller initial bundle.
- **`startTransition`**: marks a state update low-priority/interruptible so urgent updates (typing feedback) stay responsive.
- **Test behavior, not implementation**: query by role/text/label, interact like a user — implementation-detail tests break on valid refactors.
- **`interface` vs `type`**: interface for extendable object shapes; type for unions/intersections/mapped types.
- **Discriminated unions > boolean soup**: makes invalid state combinations unrepresentable, not just avoided by convention.
- **`unknown` vs `any`**: `any` disables checking; `unknown` forces narrowing/validation before use — always prefer `unknown` at trust boundaries.
- **External data**: validate at the boundary (Zod or equivalent) — a compile-time-only `as T` assertion enforces nothing at runtime.
- **Server state ≠ client state**: use React Query/SWR for fetched data (caching, revalidation); Context+`useReducer` or Zustand/Redux for genuine client state, chosen by scale and update frequency.
</content>
