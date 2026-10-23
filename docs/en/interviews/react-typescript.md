# React & TypeScript

## 🟢 Fundamentals

### React basics

#### Q1. What is JSX, and what does it actually compile to? {#jsx-compile}
JSX is syntactic sugar that lets you write markup-like syntax in JavaScript;
`<div className="a">{text}</div>` compiles (via Babel or the TypeScript compiler) to a plain
function call — historically `React.createElement('div', {className: 'a'}, text)`, or with the
newer JSX transform, an automatically-imported `jsx()` call — which returns a plain JavaScript
object describing the element (type, props, children), not a DOM node. React's reconciler later
turns that object tree into actual DOM operations. Understanding this matters because it
explains why JSX has rules JavaScript syntax doesn't (a component name must be capitalized so
the compiler treats it as a variable/function reference rather than a literal HTML tag string)
and why conditional rendering is just JavaScript expressions, not special template syntax.

**Example:**

```jsx
// what you write
const el = <Button color="blue">Save</Button>;

// what the compiler emits (new JSX transform, React 17+)
import { jsx as _jsx } from 'react/jsx-runtime';
const el = _jsx(Button, { color: 'blue', children: 'Save' });

// the result is a plain object, not a DOM node
// { type: Button, props: { color: 'blue', children: 'Save' }, key: null, ... }
<button />  // lowercase = HTML tag string 'button'
<Button />  // capitalized = reference to the Button variable
```

#### Q2. What are hooks, and what problem did they solve versus class components? {#hooks-problem-solve-class-components}
Hooks (`useState`, `useEffect`, etc.) let a function component hold state and trigger side
effects without being a class — before hooks, stateful logic required class components with
`this.state`/`this.setState` and lifecycle methods (`componentDidMount`,
`componentDidUpdate`, `componentWillUnmount`) spread across separate methods even when they
implemented one logical concern (subscribe in `componentDidMount`, unsubscribe in
`componentWillUnmount` — related code, split across the class). Hooks let that same concern live
together in one function, and critically, let stateful logic be extracted into reusable custom
hooks — something classes could only achieve through higher-order components or render props,
both of which added wrapper layers to the component tree ("wrapper hell").

**Example:**

```jsx
// Class: one concern (subscription) split across two lifecycle methods
componentDidMount()    { chat.subscribe(this.props.id, this.onMsg); }
componentWillUnmount() { chat.unsubscribe(this.props.id, this.onMsg); }

// Hooks: the same concern together, reusable as a custom hook
function useChat(id: string, onMsg: (m: string) => void) {
  useEffect(() => {
    chat.subscribe(id, onMsg);
    return () => chat.unsubscribe(id, onMsg);
  }, [id, onMsg]);
}
```

#### Q3. What's the difference between props and state, and why does data flow "down" only? {#props-state-data-flow-down}
Props are the inputs a component *receives* from its parent; state is data a component *owns* and
can change over time. A component must treat its props as read-only — it never assigns to
`props.x` — while it updates its own state through the setter (`setX`), which schedules a
re-render. Data flows one way, parent to child, through props: when a parent's state changes it
re-renders and passes new props down, and a child that needs to influence the parent does so by
calling a *function passed down as a prop* (`onChange`, `onSelect`). This makes the data flow
traceable — for any value on screen you can walk up the tree to the single component that owns
it — and it is the reason "lifting state up" (Q16) is the standard answer when two siblings need
the same data: move the state to their closest common ancestor and pass it down. The classic
mistakes are mutating a prop object or array in place (React sees the same reference, so memoized
children don't update, Q13) and duplicating a prop into state (Q17) instead of deriving from it.

**Example:**

```tsx
function Parent() {
  const [count, setCount] = useState(0);          // state: owned by Parent
  return <Child count={count} onInc={() => setCount(c => c + 1)} />;
}

function Child({ count, onInc }: { count: number; onInc: () => void }) {
  // count++;                                      // never mutate props
  return <button onClick={onInc}>{count}</button>; // data down, event up
}
```

#### Q4. `useState` vs `useRef` — when do you reach for each? {#usestate-useref-each}
`useState` triggers a re-render when its value changes, and its value is the one React renders
with on the next pass — use it for anything that should appear in the UI. `useRef` gives you a
mutable container (`.current`) that persists across renders *without* triggering a re-render
when it changes — use it for values the component needs to remember but that shouldn't drive
rendering: a DOM node reference, a timer/interval ID to clear later, or a "previous value" for
comparison. The trap: using `useRef` for something that should actually be in the UI (the value
changes but the screen never updates, since no re-render was triggered), or using `useState` for
something that doesn't need to be (causing unnecessary re-renders for a value the render output
never actually depends on).

**Example:**

```tsx
function Stopwatch() {
  const [elapsed, setElapsed] = useState(0);      // shown in the UI -> state
  const timerId = useRef<number | undefined>(undefined);                // never rendered -> ref (no re-render on write)
  const start = () => { timerId.current = window.setInterval(() => setElapsed(e => e + 1), 1000); };
  const stop = () => clearInterval(timerId.current);
  return <button onClick={elapsed ? stop : start}>{elapsed}s</button>;
}
```

#### Q5. What's the difference between a controlled and an uncontrolled form input? {#controlled-uncontrolled-form-input}
A controlled input's value is driven entirely by React state — `<input value={value}
onChange={e => setValue(e.target.value)} />` — React is the single source of truth, and every
keystroke round-trips through a state update and re-render. An uncontrolled input manages its
own internal DOM state, with React reading the current value only when needed (via a `ref`,
typically on submit) rather than on every keystroke. Controlled inputs are the default choice
because they enable real-time validation, conditional formatting, and keeping the UI in sync
with state as the user types; uncontrolled inputs avoid the per-keystroke re-render cost, which
occasionally matters for a genuinely large/complex form (see S5).

**Example:**

```tsx
// Controlled: React state is the source of truth, re-renders on every keystroke
const [email, setEmail] = useState('');
<input value={email} onChange={e => setEmail(e.target.value.trim())} />

// Uncontrolled: the DOM owns the value, read once on submit
<form onSubmit={e => { e.preventDefault(); console.log(new FormData(e.currentTarget).get('email')); }}>
  <input name="email" defaultValue="" />
</form>
```

#### Q6. When does logic belong in an event handler and when in `useEffect`? {#logic-belong-event-handler-useeffect}
Ask *why* the code runs. If it runs because **the user did something** — clicked, typed,
submitted — it belongs in the event handler: that is the moment the cause is known, it runs
exactly once per interaction, and it has access to the event. `useEffect` is for
**synchronizing with something outside React because the component is on screen or because a
rendered value changed**: opening a WebSocket subscription, starting a timer, fetching the data a
screen needs to display, setting up a listener. The frequent mistake is using an effect as a
callback chain — "when `submitted` becomes true, POST the form", or "when `items` changes, update
`total`" — which adds an extra render, hides the real cause, and misfires in development because
Strict Mode runs effects twice (S9). Rule of thumb from the React docs' "You might not need an
effect": if the value can be *computed from props and state during render*, compute it (no state, no
effect); if it's a response to a user action, do it in the handler; only what must stay in sync with
an external system after render is an effect — and it then needs a cleanup (Q11).

**Example:**

```tsx
function Cart({ items }: { items: Item[] }) {
  const total = items.reduce((s, i) => s + i.price, 0); // derived: compute in render, no state/effect

  const onSubmit = () => api.post('/orders', items);    // user action: handler

  useEffect(() => {                                     // sync with the outside world: effect + cleanup
    const ws = new WebSocket('/stock');
    return () => ws.close();
  }, []);
  return <button onClick={onSubmit}>Pay {total}</button>;
}
```

#### Q7. How does client-side routing work in a React SPA, and what belongs in the URL? {#client-side-routing-react-spa}
**Answer:** A router (React Router, TanStack Router, or the framework's router in Next.js) maps the URL to a tree of
components using the History API, without a full page reload. **Nested routes** render layouts with an `<Outlet />`
for child routes, and **route loaders** fetch data in parallel before rendering instead of waterfalls of `useEffect`.
Put in the URL anything a user should be able to **bookmark, share, or get back with the Back button**: the current
resource id, filters, sort, pagination and selected tab. Keep transient UI state (an open dropdown) in component
state. Protected routes redirect to login, but they are a UX feature: the API must still enforce authorization. The
server (or CDN) must return `index.html` for unknown paths, or deep links return 404.

**Example:**

```tsx
const router = createBrowserRouter([
  { path: '/', element: <AppLayout />, children: [
    { path: 'orders', element: <OrdersPage />, loader: ordersLoader },   // ?status=PAID&page=2
    { path: 'orders/:id', element: <OrderDetail />, loader: orderLoader },
  ]},
]);
const [params, setParams] = useSearchParams();      // filters live in the URL
```

### TypeScript

#### Q8. TypeScript `interface` vs `type` — what's the practical difference, and when do you pick one over the other? {#typescript-interface-type-practical-pick}
Both can describe an object's shape, and for that common case they're largely interchangeable.
The concrete differences: `interface` supports declaration merging (declaring the same interface
name twice merges the members — occasionally useful for extending third-party library types) and
reads slightly more naturally for extending other interfaces (`interface B extends A`); `type`
can represent things an interface can't — unions (`type Status = 'idle' | 'loading' | 'error'`),
intersections, mapped types, and conditional types. The practical rule most teams settle on:
`interface` for public object/component-prop shapes meant to be extended, `type` for unions,
utility-type compositions, and anything that isn't a plain object shape — consistency within a
codebase matters more than which specific rule is chosen.

**Example:**

```ts
interface User { id: string }
interface Admin extends User { role: 'admin' }   // extends reads naturally
interface Window { appVersion: string }          // declaration merging with the global Window

type Status = 'idle' | 'loading' | 'error';      // unions: only type can
type Keys = keyof User;                          // utility/mapped types: type
type Flags = { [K in Status]: boolean };
```

## 🟡 Senior traps

### Hooks & effects

#### Q9. What are the Rules of Hooks, and why can't a hook be called conditionally? {#rules-hooks-hook-called-conditionally}
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

#### Q10. What is a stale closure in `useEffect`, and how does the dependency array relate to it? {#stale-closure-useeffect-dependency-array}
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

#### Q11. Why does `useEffect` need a cleanup function, and what happens if you skip it for a subscription? {#useeffect-need-cleanup-function-happens}
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

### Rendering & performance

#### Q12. Why does React re-render, and how do keys affect reconciliation of a list? {#react-re-render-keys-affect}
**Answer:** A component re-renders when its own state changes, its props change, or its parent
re-renders (by default, a parent re-render cascades to re-rendering every child, regardless of
whether that child's own props actually changed, unless the child is memoized — Q13). React's
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

#### Q13. When does `React.memo` actually help, and why does it sometimes silently do nothing? {#react-memo-help-sometimes-silently}
**Answer:** `React.memo` wraps a component so it skips re-rendering if its props are shallowly
equal to the previous render's props — it helps for a component that renders expensively (or its
subtree does) and receives the same props across most of its parent's re-renders. It silently
does nothing when a prop is a new object, array, or function created inline on every parent
render (`<Child data={{ id: 1 }} />` or `<Child onClick={() => ...} />`) — a new reference every
time means the shallow-equality check always fails, so `React.memo` compares two different
objects that happen to have equal contents and (correctly, per its default shallow comparison)
decides they're different, re-rendering every time regardless. The fix is memoizing whatever's
passed as a prop with `useMemo`/`useCallback` (Q14) at the point it's created, not just wrapping
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

#### Q14. What problem do `useMemo` and `useCallback` each solve, and what's the common misuse? {#problem-usememo-usecallback-each-solve}
**Answer:** `useMemo` memoizes a computed *value*, recomputing only when its dependencies change
— useful when a computation is genuinely expensive (filtering/sorting a large array) and would
otherwise re-run on every render. `useCallback` memoizes a *function reference* itself, so the
same function identity is returned across renders as long as its dependencies don't change —
useful specifically when that function reference is passed to a memoized child (`React.memo`,
Q13) or used as another hook's dependency, since a new function reference every render would
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

#### Q15. What problem does `startTransition` / concurrent rendering solve? {#problem-starttransition-concurrent-rendering-solve}
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

### State management

#### Q16. What's "prop drilling," and how do you decide between lifting state up versus colocating it? {#prop-drilling-decide-lifting-state}
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

#### Q17. Why is copying a prop into local state via `useEffect` considered an anti-pattern? {#copying-prop-local-state-via}
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

#### Q18. When does `useReducer` fit better than `useState`? {#usereducer-fit-better-usestate}
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

#### Q19. What's the performance pitfall with React Context, and when does it become a real problem? {#performance-pitfall-react-context-become}
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

#### Q20. How do query keys work in React Query (TanStack Query), and why is it a classic source of stale or wrong data? {#query-keys-react-query-tanstack}
**Answer:** The query key is the *cache identity* **and** the dependency array of the fetch: two
components using the same key share one cached result and one in-flight request, and when the key
changes the library treats it as a different query, fetching (or serving cache for) the new one. The
rule is therefore: *every input the fetch function uses must be in the key*. Leave `page`, a filter
or a user id out and different requests collide on one cache entry — you show page 1's data on page
2, or one tenant's data to another. Three timers cause most confusion: `staleTime` (how long data
counts as fresh and won't be refetched on mount/focus — default `0`, so it refetches a lot),
`gcTime` (how long *unused* cached data is kept before garbage collection — default 5 minutes), and
`refetchOnWindowFocus`. After a mutation the cache doesn't know what changed: you must
`invalidateQueries` (by key prefix) or update the cache with `setQueryData`, otherwise lists keep
showing old values until `staleTime` expires. Structure keys hierarchically (`["orders", "list",
{ status, page }]`) so you can invalidate broad or narrow with one call.

**Example:**

```tsx
// Wrong: the key ignores `status` and `page` -> every filter shares one cache entry.
useQuery({ queryKey: ["orders"], queryFn: () => api.orders({ status, page }) });

// Right: the key contains every input; a change in status/page is a different query.
const ordersKey = (status: string, page: number) => ["orders", "list", { status, page }] as const;
useQuery({ queryKey: ordersKey(status, page), queryFn: () => api.orders({ status, page }), staleTime: 30_000 });

// After a mutation, invalidate by prefix so every cached list refetches.
const qc = useQueryClient();
useMutation({
  mutationFn: api.cancelOrder,
  onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
});
```

**Why it's a trap:** the wrong key doesn't error — it returns plausible data from *another* query, and
because the cache hides the network the bug only shows on particular navigation sequences. It often
survives review because `queryFn` closes over the variables and "looks right" (an ESLint rule,
`@tanstack/eslint-plugin-query`'s `exhaustive-deps`, catches it). See S22 for the invalidation half.

### Async UI & React 19

#### Q21. What is `Suspense`, and how does it enable code splitting? {#suspense-enable-code-splitting}
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

#### Q22. What do React error boundaries actually catch, and what do they explicitly not catch? {#react-error-boundaries-catch-explicitly}
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

#### Q23. What do React 19's Actions, `useActionState`, `useOptimistic` and `use` change about form and data-fetching code, and where are the traps? {#react-19-actions-useactionstate-useoptimistic}
**Answer:** React 19 makes the "submit, show pending, show error, update UI" loop a built-in
primitive instead of hand-written `useState` flags. An **Action** is a function (sync or async)
passed to `<form action={...}>` or run inside `startTransition`; React tracks its pending state,
resets uncontrolled fields on success, and keeps the UI responsive while it runs. `useActionState`
wraps an action and returns `[state, formAction, isPending]`, so the returned error/result and the
pending flag come from one place. `useOptimistic` lets you show the *expected* result immediately
while the action is in flight; React discards the optimistic value and shows the real state when the
transition settles — including automatically rolling back if the action throws. `use(promise)`
reads a promise during render (suspending until it resolves, so it works with `Suspense` and error
boundaries) and `use(context)` can be called conditionally, unlike `useContext`. The traps: (1) the
optimistic value is **only valid for the duration of the transition** — if you don't await the
real mutation *inside* the action, it snaps back instantly; (2) a promise passed to `use` must be
**stable across renders** (created in a parent/loader or cached) — creating it inline during render
starts a new request every render and loops forever; (3) actions resolve *sequentially* per
form/transition, so a slow action delays later ones; (4) `useFormStatus` reads the status of the
*parent* `<form>` only, so it must live in a child component.

**Example:**

```tsx
function AddTodo({ todos, addTodo }: { todos: Todo[]; addTodo: (title: string) => Promise<Todo> }) {
  const [optimisticTodos, addOptimistic] = useOptimistic(
    todos,
    (current, title: string) => [...current, { id: crypto.randomUUID(), title, pending: true }],
  );

  async function action(formData: FormData) {
    const title = String(formData.get("title"));
    addOptimistic(title);            // shown immediately
    await addTodo(title);            // must be awaited inside the action, else it reverts at once
  }                                  // on throw, the optimistic item disappears automatically

  return (
    <form action={action}>
      <input name="title" required />
      <button>Add</button>
      <ul>{optimisticTodos.map(t => <li key={t.id} style={{ opacity: t.pending ? 0.5 : 1 }}>{t.title}</li>)}</ul>
    </form>
  );
}

// Trap with use(): a new promise on every render -> suspend, resolve, re-render, new promise ...
function Profile({ id }: { id: string }) {
  const user = use(fetch(`/api/users/${id}`).then(r => r.json()));   // wrong: not stable
  return <h1>{user.name}</h1>;
}
```

**Why it's a trap:** the new APIs look like sugar but change *where* state lives. Developers keep
their `isLoading`/`error` `useState` flags and end up with two sources of truth, forget that
optimistic state is transient (the UI flashes back when the mutation isn't awaited), or create the
promise for `use` inline and produce an infinite suspend loop. Also note that the optimistic UI is a
*prediction*: the server can reject it or return a different id, so reconcile with the real response
(S19).

### TypeScript

#### Q24. Give a practical use case for TypeScript generics in a React codebase. {#practical-case-typescript-generics-react}
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

#### Q25. Why prefer a discriminated union over several boolean flags for modeling request state? {#prefer-discriminated-union-several-boolean}
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

#### Q26. Why is `unknown` considered safer than `any` in TypeScript? {#unknown-considered-safer-any-typescript}
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

#### Q27. What do `as const`, `satisfies` and an exhaustive `never` check each buy you in TypeScript? {#const-satisfies-exhaustive-never-check}
**Answer:** They are three tools for keeping *literal, precise types* without giving up
checking. **`as const`** freezes a literal: `["draft", "sent"] as const` has the type
`readonly ["draft", "sent"]` instead of `string[]`, and from it you can derive a union
(`typeof STATUSES[number]`) so the list of values and the type never drift apart. **`satisfies`**
validates that an expression *conforms* to a type without *widening* it to that type: with a type
annotation (`const routes: Record<string, Route> = ...`) you lose the specific keys and literal
values; with `satisfies` you still get an error for a wrong shape, but `routes.home` keeps its exact
type and typos in keys are still caught. An **exhaustive `never` check** (a `default` branch that
assigns the value to `never`) makes the compiler fail when a new member is added to a union and a
`switch` forgets to handle it — turning "we forgot the new status somewhere" from a production bug
into a compile error. Related trap: a TypeScript `enum` is a runtime object (numeric enums even
accept any number), so for most application code a string-literal union derived from an
`as const` array is lighter and safer.

**Example:**

```ts
const STATUSES = ["draft", "sent", "paid"] as const;
type Status = typeof STATUSES[number];               // "draft" | "sent" | "paid"

const labels = {
  draft: "Draft",
  sent: "Sent",
  paid: "Paid",
} satisfies Record<Status, string>;                  // error if a status is missing or misspelled
labels.paid;                                          // typed "Paid"-string, not just string

function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

function color(s: Status): string {
  switch (s) {
    case "draft": return "gray";
    case "sent": return "blue";
    case "paid": return "green";
    default: return assertNever(s);                  // adding "void" to STATUSES breaks the build here
  }
}
```

**Why it's a trap:** without these, code compiles with a wide `string`, an annotation that erases the
literals, or a `switch` with a silent fall-through — and the missing case surfaces as a blank badge or
`undefined` in production. `as const` is also shallow in *intent*: it makes the object read-only at
compile time only, not frozen at runtime (`Object.freeze` is the runtime tool).

### Forms & accessibility

#### Q28. How do you build a large form in React without re-render and validation problems? {#build-large-form-react-re}
**Answer:** For anything beyond a few fields, use a form library such as **React Hook Form**: it keeps inputs mostly
**uncontrolled** and registers them through refs, so typing doesn't re-render the whole form. Define validation once
as a **schema** (Zod, Yup) and derive both the runtime check and the TypeScript type from it; share the schema with
the backend if it is also TypeScript, otherwise mirror its rules with Bean Validation on the server, which stays the
source of truth. Show field errors after blur or submit, not on every keystroke. Map server-side validation errors
(400 with field details) back onto fields. Disable the submit button only while submitting, and make the submission
idempotent. With React 19, simple forms can use Actions and `useActionState` instead (see Q23).

**Example:**

```tsx
const schema = z.object({ email: z.string().email(), age: z.coerce.number().int().min(18) });
type FormValues = z.infer<typeof schema>;

const { register, handleSubmit, formState: { errors, isSubmitting } } =
  useForm<FormValues>({ resolver: zodResolver(schema), mode: 'onBlur' });
```

**Why it's a trap:** controlling every input with `useState` in one big component works for five fields and becomes
visibly laggy at fifty, and client-only validation is skipped by anyone calling the API directly.

#### Q29. What does accessibility (a11y) mean in practice for a React app? {#accessibility-a11y-practice-react-app}
**Answer:** Start with **semantic HTML**: `<button>` for actions and `<a href>` for navigation (not a clickable `<div>`),
headings in order, `<label>` tied to every input, lists as lists. That gives keyboard support and screen-reader
semantics for free. Then: everything is **reachable and operable by keyboard** with a visible focus indicator;
**manage focus** on route changes and when opening or closing modals (trap it inside, return it afterwards); give
images meaningful `alt` text (empty for decoration); don't rely on colour alone; ensure contrast (WCAG AA: 4.5:1 for
body text); and announce async updates with `aria-live`. **ARIA is a last resort**: wrong ARIA is worse than none. Check
with `eslint-plugin-jsx-a11y`, axe in tests and the browser, RTL role queries ([Testing Q7](testing.md#react-testing-library-philosophy-query)), and a manual keyboard and
screen-reader pass on key flows.

**Example:**

```tsx
// ⛔ not focusable, no role, no keyboard support
<div onClick={save}>Save</div>
// ✅
<button type="button" onClick={save}>Save</button>

<label htmlFor="email">Email</label>
<input id="email" aria-describedby="email-error" aria-invalid={!!error} />
{error && <p id="email-error" role="alert">{error}</p>}
```

**Why it's a trap:** accessibility is also a legal requirement in many markets (the European Accessibility Act applies
from June 2025), and retrofitting it into a design system is far more expensive than building it in.

### Testing

#### Q30. What should you actually test in a React component, per the React Testing Library philosophy? {#test-react-component-per-react}
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

See also: [Testing Q7, Q17, Q23](testing.md#keep-playwright-cypress-end-end) for MSW and Playwright.

## 🔴 Expert / Open

### Performance

#### Q31. A large data table becomes noticeably janky when scrolling or filtering. Walk through diagnosing and fixing it. {#large-data-table-becomes-noticeably}
Start with the React DevTools Profiler to see what's actually re-rendering and how long it takes
— don't guess. Common findings, roughly in order of likelihood: every row re-renders on every
keystroke of a filter input because the row components aren't memoized (`React.memo`) or because
they are memoized but receive a new inline function/object prop every render (Q13's trap) so the
memoization does nothing; the entire (large) dataset is rendered to the DOM at once rather than
only the visible rows, so scroll performance is bounded by total row count, not visible row
count — the fix here is list virtualization (rendering only the rows currently in or near the
viewport, e.g. `react-window`/`react-virtual`), which is the single highest-impact fix for a
genuinely large list, since it makes render cost independent of total item count; and an
expensive computation (sorting, filtering, aggregating) re-running on every render rather than
being memoized with `useMemo` keyed on the actual inputs that affect it. The senior-level
distinction: profile first, fix the specific bottleneck the profiler actually shows, rather than
reflexively wrapping everything in `memo`/`useMemo` — over-memoization has its own cost (Q14) and
doesn't help if virtualization was the real fix needed.

**Example:**

```tsx
import { FixedSizeList } from 'react-window';

const Row = memo(({ index, style, data }: ListChildComponentProps<Item[]>) => (
  <div style={style}>{data[index].name}</div>   // only ~20 rows are in the DOM
));

function Table({ items, query }: { items: Item[]; query: string }) {
  const rows = useMemo(                           // recomputed only when inputs change
    () => items.filter(i => i.name.includes(query)), [items, query]);
  return (
    <FixedSizeList height={600} width="100%" itemCount={rows.length} itemSize={36} itemData={rows}>
      {Row}
    </FixedSizeList>
  );
}
```

### State & data layer

#### Q32. How do you measure and improve frontend performance in production? {#measure-improve-frontend-performance-production}
**Answer:** Measure what users experience with **Core Web Vitals** from real users (RUM via the `web-vitals` library or
your monitoring tool), not only Lighthouse on a fast laptop. **LCP** (largest contentful paint, target < 2.5 s) is
about the critical path: server response, render-blocking CSS/JS, the hero image (preload it, serve modern formats,
correct size). **INP** (interaction to next paint, < 200 ms) is about main-thread work: long tasks, heavy re-renders,
large hydration; split work, use transitions (Q15), and virtualize big lists. **CLS** (layout shift, < 0.1) comes from
images without dimensions, late-loading fonts and injected banners. On the bundle side, the build tool (Vite/Rollup,
webpack) gives **route-level code splitting** with `lazy()`; analyse the bundle (`rollup-plugin-visualizer`) for
heavy dependencies; and set a **performance budget** in CI.

**Example:**

```text
RUM, p75 mobile:  LCP 4.1 s   INP 380 ms   CLS 0.02
LCP element: hero image 1.8 MB PNG, discovered late by JS
→ preload + AVIF + width-sized srcset: LCP 2.2 s
INP: filter input re-renders a 5,000-row table on every keystroke
→ useDeferredValue + virtualization: INP 140 ms
```

#### Q33. How do you decide between Context + `useReducer`, and a dedicated state library (Redux, Zustand, React Query)? {#decide-context-usereducer-dedicated-state}
Start from what kind of state is actually being managed, since "which library" is the wrong first
question. **Server state** (data fetched from an API, with caching, revalidation, background
refetching, and loading/error states as first-class concerns) is a fundamentally different
problem from client state, and a purpose-built tool (React Query/TanStack Query, SWR) solves it
far more completely than hand-rolling it with Context — this is usually the single highest-value
library adoption for a typical CRUD app, independent of the client-state answer. For genuine
**client state** (UI state, user preferences, anything not mirroring server data): Context +
`useReducer` is sufficient and adds no dependency when the state is small, changes infrequently,
and doesn't have the performance profile that triggers Q19's re-render problem across a large
consumer tree. Reach for a dedicated client-state library (Zustand, Redux) specifically when
state is large and frequently updated with many consumers needing only slices of it (avoiding
Q19's all-consumers-re-render problem via selectors), when the team needs strong dev tooling
(time-travel debugging, well-established middleware patterns) for a genuinely complex state
machine, or when the same state needs to be read/written from many unrelated parts of a large
codebase in a way that ad-hoc Context composition becomes hard to reason about. The
interview-worthy answer names the actual constraint driving the choice, not a library preference
stated as if it were a universal default.

**Example:**

```tsx
// Server state -> React Query (cache, refetch, loading/error for free)
const { data: orders } = useQuery({ queryKey: ['orders'], queryFn: fetchOrders });

// Small client state -> Context + useReducer, no dependency
const [cart, dispatch] = useReducer(cartReducer, []);

// Large, hot client state with slice subscriptions -> Zustand selector
const count = useCartStore(s => s.items.length); // re-renders only when length changes
```

#### Q34. Design a typed API client / data-fetching layer using TypeScript generics, with proper error handling. {#design-typed-api-client-data}
A generic request function typed on the expected response shape (`function apiRequest<T>(url:
string, schema: ZodSchema<T>): Promise<T>`) that performs the fetch, checks the HTTP status
explicitly (a non-2xx response is not automatically a JavaScript exception — `fetch` only rejects
on network failure, not on 404/500), and — critically for real type safety, not just declared
type safety — validates the parsed JSON against a runtime schema (Zod, or similar) before
returning it typed as `T`, rather than simply asserting `as T` on unchecked JSON (Q26's
`unknown`-vs-`any` point applies directly here: an external response is `unknown` until it's
actually been checked, and `as T` on unvalidated `unknown` is a compile-time-only promise the
runtime doesn't enforce, which is exactly how S16 happens). Errors are modeled as a discriminated
union result (Q25) rather than thrown exceptions for expected failure modes (a validation error,
a 404, a network failure each get their own typed variant), so callers are compiler-forced to
handle each case explicitly via the `status` narrowing, rather than an easily-forgotten
`try`/`catch` around a thrown error. Each specific endpoint then becomes a thin, fully-typed
wrapper: `getUser(id: string) { return apiRequest(`/users/${id}`, userSchema); }`.

**Example:**

```ts
import { z } from 'zod';

type Result<T> =
  | { status: 'ok'; data: T }
  | { status: 'http-error'; code: number }
  | { status: 'invalid'; issues: z.ZodIssue[] }
  | { status: 'network-error' };

async function apiRequest<T>(url: string, schema: z.ZodType<T>): Promise<Result<T>> {
  let res: Response;
  try { res = await fetch(url); } catch { return { status: 'network-error' }; }
  if (!res.ok) return { status: 'http-error', code: res.status }; // fetch doesn't reject on 404/500
  const parsed = schema.safeParse(await res.json());              // unknown until validated
  return parsed.success ? { status: 'ok', data: parsed.data } : { status: 'invalid', issues: parsed.error.issues };
}

const getUser = (id: string) => apiRequest(`/users/${id}`, userSchema);
```

### Typing

#### Q35. How do you type a design-system component that supports an `as` prop (a polymorphic `Button` that can render `<a>`, `<button>` or a router `Link`)? {#type-design-system-component-supports}
The goal is that the component accepts *the props of whatever element it renders* and rejects
props that element doesn't have (`href` on a `<button>`, `type` on an `<a>`). The naive approach —
`props: any`, or a hand-written union of every element's props — either loses checking or does not
scale. The idiomatic solution is a generic over the element type, `C extends React.ElementType`, and
props built as *your own props merged with the chosen element's props minus the overlap*:
`PolymorphicProps<C, Own> = Own & Omit<React.ComponentPropsWithoutRef<C>, keyof Own> & { as?: C }`.
Callers then get `href` autocomplete when `as="a"` and a compile error when they pass `href` to a
`button`. Add a `ref` variant via `ComponentPropsWithRef` or React 19's `ref` as a plain prop. Two
caveats: inference on generic components with complicated conditional types gets slow and produces
unreadable errors, so keep the type in one well-tested helper; and the flexibility has an
accessibility cost, because `as="div"` with `onClick` loses keyboard and role semantics — the
design system should restrict `as` to a set of valid elements and bake accessibility in (or offer
explicit variants such as `ButtonLink`) rather than allowing anything. Often the more maintainable
alternative to `as` is composition — a `asChild` pattern (Radix `Slot`) that merges props into the
single child — or separate components sharing styles, which trades a little duplication for much
simpler types. Decide by how many consumers there are: a public design system justifies the generic
type; an application-internal button rarely does.

**Example:**

```tsx
import type { ElementType, ComponentPropsWithoutRef } from 'react';

type ButtonProps<C extends ElementType> = {
  as?: C;
  variant?: 'primary' | 'ghost';
} & Omit<ComponentPropsWithoutRef<C>, 'as' | 'variant'>;

function Button<C extends ElementType = 'button'>({ as, variant = 'primary', ...rest }: ButtonProps<C>) {
  const Tag: ElementType = as ?? 'button';
  return <Tag className={`btn btn-${variant}`} {...rest} />;
}

<Button as="a" href="/home">Home</Button>   // OK: href is valid on <a>
<Button href="/home">Home</Button>          // error: href doesn't exist on <button>
```

### Architecture

#### Q36. When would you adopt React Server Components (RSC), and what do they cost you? {#adopt-react-server-components-rsc}
RSC render on the server (at request or build time) and send the client a serialized tree instead
of JavaScript: a Server Component can `await` a database or an API directly, its code and its heavy
dependencies (a Markdown parser, a date library) **never ship to the browser**, and secrets stay on
the server. Client Components (marked `"use client"`) are still needed for state, effects, event
handlers and browser APIs, and they hydrate as usual. The benefits are smaller bundles, fewer
client-side request waterfalls (data is fetched next to where it's rendered, close to the data
source), and streaming with `Suspense`. The costs are real: a **two-environment mental model** (what
runs where, what can be passed across the boundary — only serializable props, no functions from a
Server to a Client Component except Server Actions), a **framework dependency** (in practice Next.js
App Router or similar, with a bundler/router integration), harder testing and local debugging,
server infrastructure and caching semantics to understand (per-request memoization, what is cached
and when it's revalidated), and easy ways to lose the benefit — one `"use client"` at the top of a
layout pulls every import beneath it into the client bundle. I would choose RSC for content-heavy or
data-heavy pages where first load and SEO matter and the team can invest in the framework; I would
stay with a client-rendered SPA plus React Query for an authenticated, highly interactive
application behind a login (dashboards, editors), where there's little SEO value and most of the
UI is client state anyway. Either way keep the boundary deliberate: push `"use client"` down to the
leaves (a button, a chart), pass server data in as props, and measure bundle size and
time-to-interactive before and after rather than adopting it for fashion.

**Example:**

```tsx
// app/products/page.tsx -- Server Component (default): runs on the server only
import { AddToCart } from './AddToCart';

export default async function Page() {
  const product = await db.product.find(1);   // direct DB access, secrets stay server-side
  return (
    <section>
      <h1>{product.name}</h1>
      <AddToCart id={product.id} />          {/* serializable props only */}
    </section>
  );
}

// AddToCart.tsx
'use client';                                // client leaf: state + handlers
export function AddToCart({ id }: { id: number }) { /* useState, onClick... */ }
```

#### Q37. When are micro-frontends a good idea, and what are the alternatives? {#micro-frontends-good-idea-alternatives}
Micro-frontends split one web application into independently built and deployed frontends, composed
in the browser (Module Federation, web components, iframes) or at the edge/server. The real
problem they solve is *organizational*: many teams that must ship on their own cadence without
coordinating a release of one big bundle, or a gradual migration (a legacy AngularJS app strangled
piece by piece into React). They do not make an application faster or simpler; the price is duplicate
dependencies unless carefully shared (two Reacts on a page break hooks), inconsistent look and feel,
harder cross-cutting concerns (auth, routing, analytics, error handling, one shared design system),
a runtime integration contract that is versioned and tested like an API, and more infrastructure
(each fragment has its own pipeline, and end-to-end tests are needed across them). Alternatives
that usually deliver the team autonomy at less cost: a **modular monorepo** with enforced module
boundaries (nx/Turborepo, lint rules for import restrictions), a shared design-system package
published with semantic versions, and feature flags with trunk-based development so teams deploy
independently *without* separate runtime bundles. My rule: start with a modular monolith; introduce
micro-frontends only when the organization (10+ frontend engineers, distinct domains and release
cycles) or a migration demands independent deploys, choose a small number of coarse-grained slices
along business domains (never one per component), and decide up front how routing, shared state
(URL, events — not a shared global store) and the design system work between them.

**Example:**

```js
// Module Federation (webpack/rspack): the shell loads a remote at runtime
new ModuleFederationPlugin({
  name: 'shell',
  remotes: { checkout: 'checkout@https://cdn.example.com/checkout/remoteEntry.js' },
  shared: { react: { singleton: true }, 'react-dom': { singleton: true } }, // one React only
});
// const Checkout = lazy(() => import('checkout/App'));   // deployed independently by team Checkout
```

#### Q38. SPA, SSR, SSG or React Server Components — how do you choose a rendering strategy? {#spa-ssr-ssg-react-server}
**Answer:** Decide per route, based on **SEO needs, data freshness, personalization and infrastructure**. A **SPA**
(Vite + React, served from a CDN) suits apps behind login, such as back-offices and dashboards: simple hosting and a
clear API boundary, but a slower first load and weak SEO. **SSG** (pre-render at build time) suits content that rarely
changes, such as marketing pages and docs: fastest and cheapest. **SSR** renders HTML per request for SEO and fast first
paint with fresh or personalized data, at the cost of running and scaling a Node server and handling hydration. **ISR**
(regenerate static pages on a timer or on demand) sits between SSG and SSR. **Server Components** (Next.js App Router)
render on the server and send no JS for non-interactive parts (see Q36). For a Java-backend team, a common split is a
SPA for the product, plus SSG/SSR in Next.js only for public pages.

#### Q39. How do you build an accessible slot picker for booking an appointment? {#build-accessible-slot-picker-booking}
**Answer:** Use native semantics before ARIA. Each day is a `<fieldset>` with a `<legend>` (the full date as text), and each slot is a radio input with a visible label, so the keyboard, screen readers and form submission work without custom code. Arrow keys move between the radios of a group, and Tab moves between groups. Say the time zone when it can differ from the patient's ("times are in the practice's local time, Paris"). Announce loading, "no availability this week" and errors in an `aria-live="polite"` region. Do not rely on colour alone for selected or unavailable states. When booking fails because the slot was just taken (`409`), keep the user's other choices, refresh the slots, and move focus to the error message. Test with the keyboard only and with a screen reader, and add axe checks in CI ([Q29](react-typescript.md#accessibility-a11y-practice-react-app)).

**Example:**

```tsx
function DaySlots({ day, slots, selected, onSelect }: Props) {
  const label = new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long", timeZone }).format(day);
  return (
    <fieldset>
      <legend>{label}</legend>
      {slots.length === 0 && <p>No availability</p>}
      {slots.map((s) => (
        <label key={s.start}>
          <input type="radio" name="slot" value={s.start}
                 checked={selected === s.start} onChange={() => onSelect(s.start)} />
          {formatTime(s.start, timeZone)}
        </label>
      ))}
    </fieldset>
  );
}
// Elsewhere: <div aria-live="polite">{status}</div> for "loading", "slot taken, please choose another"
```

**Why it's a trap:** a grid of clickable `<div>`s looks right and works with a mouse only. Health booking is used by elderly patients and people with disabilities, and accessibility is often a legal requirement for this kind of service.

#### Q40. How do you handle translations, dates and time zones in a React app used in several countries? {#handle-translations-dates-time-zones}
**Answer:** Translations: an i18n library with ICU messages (react-intl or i18next) to handle plurals and variables, no string concatenation, translation bundles lazy-loaded per locale, and a pseudo-locale in tests to spot hard-coded or truncated text. Dates: the API sends **instants** in ISO-8601 UTC plus the practitioner's **IANA time zone** (`Europe/Paris`), because an appointment happens at the practice's local time. Format with `Intl.DateTimeFormat(locale, { timeZone })`, and show the zone when the patient's browser is elsewhere. Never parse `new Date("2026-10-19")`: that date-only string is read as UTC midnight and can display as the previous day. Use a library (date-fns-tz, Luxon) or `Temporal` where supported for time-zone arithmetic. Locale also drives number, currency and address formats, and the first day of the week.

**Example:**

```tsx
const fmt = new Intl.DateTimeFormat(locale, {
  weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: appointment.timeZone,
});
<FormattedMessage id="booking.slots"
  defaultMessage="{count, plural, =0 {No slot} one {# slot} other {# slots}} available" values={{ count }} />
<time dateTime={appointment.start}>{fmt.format(new Date(appointment.start))}</time>
```

**Why it's a trap:** formatting in the browser's time zone. A patient in Lisbon booking a doctor in Paris sees a time one hour off and arrives late. The bug is invisible to a developer whose laptop is in the practice's zone.

## 🎯 Real-world scenarios

### S1. A component enters an infinite re-render loop, freezing the tab {#component-enters-infinite-re-render}
- **Symptoms:** The browser tab becomes unresponsive, React DevTools (if it loads at all) shows
  an endlessly incrementing render count, and the console may show a "Maximum update depth
  exceeded" error.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S2. A counter displayed via `setInterval` inside `useEffect` always shows the same value, never incrementing {#counter-displayed-via-setinterval-inside}
- **Symptoms:** A component sets up `setInterval` in a `useEffect` to log or display a state
  value periodically, but the value shown never changes from what it was on the very first
  render, even though the actual state elsewhere in the app has since updated.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classic stale closure (Q10) — the effect's `[]` (empty) dependency array means the
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

</details>

### S3. The console repeatedly logs "Can't perform a React state update on an unmounted component" {#console-repeatedly-logs-perform-react}
- **Symptoms:** This warning appears, usually after navigating away from a page quickly, or when
  a slow network response returns after the user has already moved on.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** An async operation (a fetch, a subscription callback) was started while the
  component was mounted, and its `.then()`/callback calls `setState` after the component has
  since unmounted — the async operation doesn't know or care that its component is gone by the
  time it resolves.
- **Example:**

  ```text
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

</details>

### S4. A large table becomes visibly janky (dropped frames, laggy scrolling) once it has a few thousand rows {#large-table-becomes-visibly-janky}
- **Symptoms:** Scroll performance is smooth with a small dataset but degrades sharply as row
  count grows into the thousands, well before the data itself would be considered "large" by
  backend standards.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Confirmed with the Profiler (Q31) — the entire dataset is being rendered to
  actual DOM nodes at once, so both initial render and any scroll-triggered work scale with total
  row count rather than visible row count.
- **Example:**

  ```text
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

</details>

### S5. Typing in a text input feels laggy, with visible delay between a keystroke and the character appearing {#typing-text-input-feels-laggy}
- **Symptoms:** A controlled input's perceived responsiveness degrades noticeably, especially in
  a form embedded within a larger, complex page.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

- **Resolution:** Move the input's own state as local as possible (colocation, Q16) so its
  `setState` only re-renders the input itself and its immediate surroundings, not the whole page;
  memoize expensive sibling/parent subtrees so they don't re-render just because unrelated local
  state changed; for genuinely expensive downstream work driven by the input's value (e.g.
  filtering a large list as the user types), debounce that work or wrap it in `startTransition`
  (Q15) so it doesn't block the input's own immediate visual feedback.
- **Prevention:** Keep form input state colocated with the input by default, and treat any
  "typing feels laggy" report as a state-placement/memoization question to profile immediately,
  rather than something to work around with throttling alone.

</details>

### S6. Changing a small piece of app-wide state (e.g. toggling dark mode) causes a noticeable, visible re-render across the entire page {#changing-small-piece-app-wide}
- **Symptoms:** A single global setting change (theme, language, feature flag) causes a visible
  flash/re-render across large parts of the UI that have nothing to do with that setting.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** All that state lives in one shared Context whose consumers span most of the
  component tree, and Context's all-consumers-re-render-on-any-change behavior (Q19) means a
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

</details>

### S7. The app crashes in production with a runtime type error, despite the TypeScript build passing cleanly {#app-crashes-production-runtime-type}
- **Symptoms:** `TypeScript compiled with 0 errors`, yet a production error-tracking tool shows a
  `TypeError: cannot read property 'x' of undefined` on a value the type system claimed was
  always present.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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
  as a code-review flag requiring justification — `unknown` plus explicit validation (Q26, Q34)
  should be the default pattern for any external data boundary, not an occasional hardening
  measure.

</details>

### S8. Search results occasionally show results for a previous, already-abandoned search query {#search-results-occasionally-show-results}
- **Symptoms:** Typing quickly in a search box sometimes results in the displayed results
  reverting to (or flickering to) results for an earlier, shorter query, even though the input
  itself shows the latest typed text.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S9. An API endpoint is called twice for what should be a single component mount {#api-endpoint-called-twice-single}
- **Symptoms:** Network tab shows the same GET request firing twice in quick succession when a
  component first renders, in development specifically (and the team is confused whether this
  also happens in production).

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** In development, React's `StrictMode` deliberately double-invokes certain
  lifecycle-equivalent behavior (mounting, unmounting, and re-mounting a component, and thus
  re-running effects) specifically to help surface effects that aren't properly cleaned up — this
  is intentional, development-only behavior, not a production bug, *if* the effect's cleanup
  function correctly cancels/undoes the first invocation's work. If it also happens in
  production, the actual cause is more likely a missing or incorrect dependency array causing a
  genuine duplicate effect run outside of `StrictMode`'s deliberate double-invoke.
- **Example:**

  ```text
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

</details>

### S10. A refactor to pass a new value through five layers of components becomes a large, error-prone diff {#refactor-pass-new-value-five}
- **Symptoms:** Adding one new piece of data that a deeply nested component needs requires
  touching every intermediate component's props interface along the path to it, for data those
  intermediate components don't otherwise use.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** This is prop drilling (Q16) reaching the point where it's actively costly — the
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
  changing or large shared state, this is the point to evaluate a dedicated state library (Q33)
  instead of solving it with Context alone.
- **Prevention:** Treat "does this value need to pass through components that don't use it" as a
  design question when a data dependency is first introduced, not just when the drilling has
  already spread across five layers and refactoring becomes expensive.

</details>

### S11. An error thrown inside a button's `onClick` handler crashes the whole page instead of being caught by the app's error boundary {#error-thrown-inside-button-onclick}
- **Symptoms:** The team added an error boundary wrapping the app specifically to prevent a
  full-page crash on unexpected errors, but a bug in an `onClick` handler still produces a blank
  white screen (or an unhandled console error) instead of the expected fallback UI.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Error boundaries don't catch event handler errors by design (Q22) — the handler
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

</details>

### S12. Initial page load time is slow, and the network tab shows a very large single JavaScript bundle {#initial-page-load-time-slow}
- **Symptoms:** Time-to-interactive is high even on a fast connection, and the bundle analyzer
  shows one large `main.js` containing code for routes/features most users on this initial page
  never visit.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** No code splitting is in place — every route and feature, including rarely-used
  ones (an admin panel, a settings page, a rarely-opened modal's heavy dependency), is bundled
  into the initial load regardless of whether the current page needs it.
- **Example:**

  ```bash
  $ npx source-map-explorer build/static/js/main.*.js
  # main.js: 3.8 MB — includes the admin panel, the rich-text editor, and a charting
  # library, none of which the landing page (the most-visited route) ever renders.
  ```

- **Resolution:** Introduce route-level code splitting with `React.lazy` and `Suspense` (Q21) at
  minimum, so each route's code is a separate chunk fetched only when navigated to; for
  particularly heavy individual features within a route (a rich text editor, a charting library),
  split those out too and lazy-load them on interaction (e.g. only when a specific tab is opened)
  rather than bundling them with the route that merely contains the option to open them.
- **Prevention:** Run a bundle analyzer as part of the regular build/review process (not just
  once, retroactively) so a large new dependency being added to the initial bundle is caught at
  the PR that introduces it.

</details>

### S13. A refactor that doesn't change any user-facing behavior breaks a large fraction of the test suite {#refactor-doesn-change-any-user}
- **Symptoms:** Renaming an internal state variable, converting a component from `useState` to
  `useReducer` internally, or restructuring how a component is composed internally — none of
  which change what the user sees or can do — causes many tests to fail.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The test suite is asserting on implementation details (internal state shape,
  specific internal method calls, shallow-rendered component tree structure) rather than
  user-observable behavior — the anti-pattern Q30 describes, often from testing utilities/patterns
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

</details>

### S14. Items in a reorderable list occasionally show the wrong content, or lose their local input state, after being reordered {#items-reorderable-list-occasionally-show}
- **Symptoms:** A drag-to-reorder list, or a list where items can be inserted/removed from the
  middle, shows a mismatch after reordering — an item's checkbox state, or an input's typed
  value, appears attached to the wrong row after the reorder.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S15. A component's displayed value silently drifts out of sync with the prop it was supposed to reflect {#component-displayed-value-silently-drifts}
- **Symptoms:** A component that copies an incoming prop into local state (to allow local editing
  before save) sometimes shows stale data after the prop updates elsewhere, or loses a user's
  in-progress local edit when the prop happens to update for an unrelated reason.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** This is exactly Q17's anti-pattern — syncing a prop into state via `useEffect`
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

</details>

### S16. The TypeScript build is clean, but the app crashes when parsing a third-party API's response {#typescript-build-clean-but-app}
- **Symptoms:** A recently integrated external API occasionally returns a field as `null` where
  the TypeScript interface declares it as a required `string`, and the app crashes trying to call
  a string method on it — the compiler never flagged this because it has no way to verify an
  external HTTP response actually matches a hand-written interface.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The interface describing the API response was written by hand (or generated once
  from a sample response) and asserted onto the parsed JSON, rather than validated — TypeScript
  types are erased at compile time ([Java Q10](java-core-jvm.md#type-erasure-break)'s erasure point applies analogously here) and
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
  as `unknown` and validated at the boundary by default (Q26, Q34) — a hand-written interface with
  no runtime check is a promise the compiler makes on the codebase's behalf that it has no actual
  ability to keep.

</details>

### S17. The console shows "Text content does not match server-rendered HTML" and the page flickers or renders wrongly after load {#console-shows-text-content-match}
- **Symptoms:** On a server-rendered (Next.js/Remix) page, the console logs `Hydration failed
  because the server rendered HTML didn't match the client` (or "Text content does not match").
  Users see a flash of the wrong value — the wrong time, a logged-out header for a logged-in
  user — and sometimes React discards the server HTML and re-renders the whole subtree on the
  client, losing the SSR performance benefit. It never reproduces in a purely client-rendered dev build.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Hydration requires the *first client render* to produce exactly the markup the server
  sent. Anything that differs between the two environments breaks that: `Date.now()`, `new Date()`
  formatted in the server's time zone vs the browser's, `Math.random()`/`crypto.randomUUID()` for ids,
  `window`/`localStorage` checks (`typeof window !== "undefined"` branches), locale formatting, or
  invalid HTML nesting (a `<div>` inside a `<p>` that the browser "repairs"). Read the diff shown in the
  dev overlay to find the element, then look for one of those inputs in its render path.
- **Example:**

  ```tsx
  function Greeting() {
    const hour = new Date().getHours();                 // server: UTC, client: user's time zone
    const theme = localStorage.getItem("theme") ?? "light";  // throws on the server / differs on client
    return <p className={theme}>{hour < 12 ? "Good morning" : "Good afternoon"}</p>;
  }
  ```

- **Resolution:** Make the first render deterministic and move environment-specific values to after
  hydration: read browser-only data in `useEffect` (state starts with the server-safe default and is
  updated once mounted), use `useId` for generated ids, pass the server-computed timestamp/locale as a
  prop so both sides format the same value, and fix invalid nesting. For a truly client-only widget,
  render it via a client-only wrapper (dynamic import with SSR disabled) or use
  `suppressHydrationWarning` only for unavoidable one-element differences such as a timestamp.
  Verify that the console is clean on a hard reload with the production build.
- **Prevention:** Lint for `window`/`Date.now`/`Math.random` in render paths of SSR components,
  run the E2E suite against the production SSR build and fail on console hydration errors, and treat
  "render must be pure and identical on both sides" as a component-design rule (Q6).

</details>

### S18. Every keystroke in a form field loses focus after one character {#every-keystroke-form-field-loses}
- **Symptoms:** In a settings form, typing in an input works for one character and then the cursor
  disappears; the user must click again for each character. Local state inside the field (a
  scroll position, an open dropdown) also resets on every keystroke. The bug appeared after a
  developer "tidied up" the file by extracting a sub-component.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The input is being **unmounted and re-mounted** on every render. React identifies a
  component by its *type* at a position in the tree; if a component function is defined *inside*
  another component's body, it is a brand-new function (a new type) on every render of the parent, so
  React discards the old subtree — DOM node, focus and state included — and builds a new one. The
  parent re-renders on every keystroke because the state lives there. Confirm in the Profiler or by
  logging in an effect with `[]` deps inside the child: it fires on every keystroke (Q12's key/identity
  rule applies to types as well).
- **Example:**

  ```tsx
  function Settings() {
    const [name, setName] = useState("");

    function NameField() {                     // new component type on every Settings render
      return <input value={name} onChange={e => setName(e.target.value)} />;
    }

    return <NameField />;                      // unmounted and remounted on each keystroke
  }
  ```

- **Resolution:** Define the component at module level and pass what it needs as props (or call it as
  a plain function returning JSX if it must close over local values, which avoids creating a new
  component type). Verify by typing a long string without losing focus and with a mount-effect log that
  fires once.
- **Prevention:** Enable `react/no-unstable-nested-components` in ESLint, review any component
  declared inside another, and colocate small sub-components in the same *file* — not the same function.

</details>

### S19. A "like" button with an optimistic update flickers back and forth and finally shows the wrong count {#like-button-optimistic-update-flickers}
- **Symptoms:** Users double-click a like button. The counter jumps up, drops, jumps up again, then
  settles on a value that doesn't match the server after a refresh. On flaky mobile connections the
  UI shows "liked" even though the request failed and nothing was saved.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The optimistic update writes to the cache/state but doesn't handle three things:
  (1) **in-flight refetches** that finish after the optimistic write and overwrite it with the old
  server value (the flicker), (2) **rollback** when the request fails — with no `onError` restoring the
  previous value the wrong state stays, and (3) **concurrent mutations** whose responses arrive out of
  order, each applying a result computed from a stale snapshot (Q23's caveat that optimistic values are
  predictions). Reproduce with the network tab throttled and requests delayed unevenly.
- **Example:**

  ```tsx
  useMutation({
    mutationFn: api.like,
    onMutate: (id) => {
      qc.setQueryData<Post>(["post", id], p => p && { ...p, likes: p.likes + 1 });   // no snapshot, no cancel
    },
    // no onError rollback; no onSettled invalidation
  });
  ```

- **Resolution:** Follow the full optimistic pattern: in `onMutate` cancel outgoing refetches for that key
  (`await qc.cancelQueries`), snapshot the previous value and return it as context; in `onError`
  restore the snapshot; in `onSettled` invalidate the key so the cache converges on the server truth.
  Prevent double submission by disabling the button while pending, and send an idempotency key or
  a desired *state* (`liked: true`) rather than an increment so retries don't count twice. Verify with a
  throttled-network test: rapid clicks, then forced failure — the UI returns to the correct state.
- **Prevention:** Put optimistic mutations in one shared hook pattern, make mutations idempotent on
  the server, and add a test with a delayed/failed mock response for every optimistic interaction.

</details>

### S20. The initial JavaScript bundle doubled after a "harmless" refactor; Lighthouse score dropped {#initial-javascript-bundle-doubled-after}
- **Symptoms:** After adding a small utility import, the main bundle grew from ~300 KB to ~900 KB (gzip),
  first-load time on mobile slipped by seconds, and CI's bundle-size check (or Lighthouse) started warning.
  The changed code only imports one icon and one helper function.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Open a bundle analyzer (`vite-bundle-visualizer`, `webpack-bundle-analyzer`,
  `source-map-explorer`) and find the large chunk. Typical culprits: a **barrel file**
  (`components/index.ts` re-exporting everything) or a package whose entry re-exports thousands of
  modules (an icon library, `lodash` instead of `lodash-es`), where the bundler can't prove side-effect
  freedom and keeps everything, defeating tree-shaking; a heavy library (a chart or editor) pulled into
  the initial chunk because it's imported statically; or a Server/Client boundary put too high. Check
  `sideEffects` in the package.json and how the import is written.
- **Example:**

  ```ts
  import { format } from "lodash";                    // whole library (CommonJS, not tree-shakable)
  import { Icon } from "@/components";                // barrel: pulls every component and their deps
  import { HugeChart } from "./HugeChart";            // static import: in the initial bundle
  ```

- **Resolution:** Import at the granular path (`import format from "lodash/format"`, `lodash-es`, or
  the library's per-icon entry points), import from the component's file rather than the barrel,
  set `"sideEffects": false` where valid, and lazy-load heavy, below-the-fold or route-level modules with
  `React.lazy` + `Suspense` (Q21). Re-run the analyzer and confirm the initial chunk returns to the
  baseline.
- **Prevention:** A **bundle-size budget in CI** (`size-limit` or bundlesize) that fails the PR,
  an ESLint rule restricting barrel/large-library imports, and a periodic analyzer review; prefer
  smaller libraries or native APIs (`Intl`, `Date`) over heavy dependencies for small needs.

</details>

### S21. A long-lived single-page app gets slower and its memory grows steadily until the tab crashes {#long-lived-single-page-app}
- **Symptoms:** A dashboard left open on a wall display for a day becomes sluggish and eventually
  crashes ("Aw, Snap"). The Chrome Task Manager shows memory growing with each data refresh or route
  change; resizing or navigating makes handlers fire multiple times.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Take **heap snapshots** (DevTools → Memory) before and after repeating an action
  such as navigating away and back, and compare: growing counts of detached DOM nodes,
  event listeners, closures or arrays point at what is retained. The usual causes are effects that
  register a listener, interval or subscription (`window.addEventListener("resize", ...)`,
  a WebSocket, a store `subscribe`) without a cleanup function (Q11), so every mount adds another one
  that also captures the component's props/state in its closure; unbounded caches or arrays that
  only append (a message log that is never trimmed); and module-level singletons holding component references.
- **Example:**

  ```tsx
  useEffect(() => {
    const onTick = (m: Message) => setMessages(prev => [...prev, m]);   // grows forever
    socket.on("message", onTick);                                       // never removed
  }, []);                                                               // each remount adds another listener
  ```

- **Resolution:** Return a cleanup that removes the listener (`return () => socket.off("message", onTick)`),
  cap collections (keep the last N messages, or virtualize and paginate), close sockets and abort fetches in
  cleanup, and drop references from module-level caches on unmount. Verify by repeating the heap-snapshot
  comparison across 50 navigations: the retained size stays flat and listener counts no longer climb.
- **Prevention:** Strict Mode in development double-invokes effects, which exposes missing cleanup early
  — keep it on. Prefer libraries that manage subscription lifecycle (React Query, `useSyncExternalStore`),
  add a soak test for long-running screens, and review any `addEventListener`/`setInterval`/`subscribe` in an effect for its counterpart.

</details>

### S22. After editing a record, the list page still shows the old data until the user reloads {#after-editing-record-list-page}
- **Symptoms:** A user renames a customer in a form and returns to the customer list, which still shows the
  old name. A refresh fixes it. Sometimes the detail page is updated but the list, a dashboard widget and a
  dropdown elsewhere are not.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** With a server-state cache (React Query/SWR) the cache holds each query under its
  key and has no idea a mutation changed the underlying data (Q20). Neither `invalidateQueries` nor a
  `setQueryData` was called for *all* the keys that display the record, or the invalidation used a
  key that didn't match the prefix of the cached list (`["customers"]` vs `["customer-list", { page }]`).
  Inspect the cache in the React Query DevTools: the list query is `fresh` for the `staleTime` window
  and never refetches on remount.
- **Example:**

  ```tsx
  const update = useMutation({ mutationFn: api.updateCustomer });          // no cache handling at all
  // list:   useQuery({ queryKey: ["customer-list", { page }], staleTime: 5 * 60_000, ... })
  // detail: useQuery({ queryKey: ["customer", id], ... })
  ```

- **Resolution:** In `onSuccess` invalidate by hierarchical prefix — `qc.invalidateQueries({ queryKey: ["customers"] })`
  — after restructuring keys as `["customers", "list", {...}]` and `["customers", "detail", id]`; for instant
  feedback write the returned entity with `setQueryData` and invalidate the lists. Verify with a test:
  mutate, navigate back and assert the new name renders without a reload.
- **Prevention:** Centralize key factories (`customerKeys.all`, `.list()`, `.detail(id)`) next to the API
  functions, so keys and invalidations can't drift; keep `staleTime` deliberate rather than large "to save
  requests"; and make "which queries display this entity?" a checklist item for each mutation.

</details>

## 🗣️ Commonly asked questions

Questions that come up often in interviews on this topic (a typical set, not tied to one specific interview). Each has a short model answer: expand it with the sections above and say it aloud.

#### R1. `useEffect` vs `useLayoutEffect`. {#useeffect-uselayouteffect}
**Answer:** `useEffect` runs after the browser has painted, so it does not block rendering: use it for data fetching and subscriptions. `useLayoutEffect` runs synchronously after DOM updates but before paint: use it only to measure or adjust layout and avoid a visible flicker. It blocks painting, so keep it short.

#### R2. Controlled vs uncontrolled components. {#controlled-uncontrolled-components}
**Answer:** Controlled: React state is the source of truth (`value` + `onChange`), which makes validation and conditional UI easy but re-renders on each keystroke. Uncontrolled: the DOM holds the value, read through a `ref` or `FormData` on submit; simpler and cheaper for big forms. Libraries such as React Hook Form use the uncontrolled approach for performance.

#### R3. `type` vs `interface` in TypeScript. {#type-interface-typescript}
**Answer:** Both describe object shapes. `interface` can be extended and merged (declaration merging) and gives clearer errors; `type` also handles unions, intersections, tuples and mapped types. A common rule: `interface` for public object contracts, `type` for unions and compositions; be consistent in a codebase.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. What is JSX, and what does it actually compile to?
2. Q4. `useState` vs `useRef` — when do you reach for each?
3. Q8. TypeScript `interface` vs `type` — what's the practical difference, and when do you pick one over the other?
4. Q9. What are the Rules of Hooks, and why can't a hook be called conditionally?
5. Q19. What's the performance pitfall with React Context, and when does it become a real problem?
6. Q30. What should you actually test in a React component, per the React Testing Library philosophy?
7. Q31. A large data table becomes noticeably janky when scrolling or filtering. Walk through diagnosing and fixing it.
8. Q37. When are micro-frontends a good idea, and what are the alternatives?
9. S1. A component enters an infinite re-render loop, freezing the tab
10. S22. After editing a record, the list page still shows the old data until the user reloads

## 📌 Cheat-sheet

### Core React

> **Start here:** props come down and events go up, state drives the UI, derive instead of syncing, and call hooks unconditionally.

- **Props vs state** — props are read-only inputs from the parent; state is owned by the component and updated via its setter. *Data flows down, events flow up via callback props.*
- **Hooks** — functions like `useState`/`useEffect` that give function components state and effects. *They give the same "stateful logic together" benefit classes couldn't offer without wrapper hell. They must be called unconditionally, in the same order every render (no hooks inside `if`).*
- **`useState` vs `useRef`** — state triggers a re-render and drives the UI. A ref persists a mutable value without triggering one. *Use refs for DOM nodes, timers, non-UI values.*
- **Handler vs effect** — user action → event handler. Sync with an external system → effect (with cleanup). Derivable from props/state → compute during render. *Effect callback chains add renders and hide causes.*
- **Don't sync props → state via `useEffect`** — derive the value during render instead. *For an intentional local copy, remount via `key`.*
- **`key`** — a stable per-item ID, e.g. `<li key={user.id}>`. *Never the array index for a reorderable/mutable list: wrong key = state/content attached to the wrong row.*
- **Never define a component inside a component** — a new component type per render means remount, lost focus and lost state.

### Effects and closures

> **Start here:** an effect sees the values from the render that created it, and anything it starts must be stopped in cleanup.

- **Stale closure** — an effect's captured values are frozen at creation time. *`[]` deps + reading a changing value = bug.*
- **Functional updates** — `setCount(c => c + 1)` instead of `setCount(count + 1)`. *Sidesteps stale closures.*
- **Effect cleanup** — the function an effect returns, run before the next run/unmount. *Required for anything that outlives one run: subscriptions, intervals, listeners, in-flight fetches (`AbortController`).*
- **Memory leaks in SPAs** (single-page apps) — caused by uncleaned listeners/subscriptions and append-only arrays. *Fix: heap-snapshot diff, add cleanups, cap collections.*
- **Error boundaries** — catch render/lifecycle errors only. *Not event handlers, not async code; those need their own `try`/`catch`.*

### Performance

> **Start here:** measure first; most apps need little memoization. Fix new-object-every-render at the source and split what is big.

- **`useMemo`/`useCallback`** — memoize an expensive computation / keep a function identity stable for memoized children. *Profile before applying; don't default to it everywhere.*
- **`React.memo`** — skips re-render when props are shallow-equal. *Useless if the parent passes new inline objects/functions every render: memoize at the source, not just the receiver.*
- **Context** — all consumers re-render on any value change. *For frequently-updated, widely-consumed state, split into narrow contexts and memoize the value object.*
- **`Suspense` + `React.lazy`** — route/feature-level code splitting. *Smaller initial bundle.*
- **`startTransition`** — marks a state update low-priority/interruptible. *Urgent updates (typing feedback) stay responsive.*
- **Bundle size** — barrel files (`index.ts` re-exporting everything) and non-tree-shakable packages defeat tree-shaking. *Analyze, import granularly, lazy-load heavy routes, enforce a CI size budget.*
- **Hydration mismatch** (server HTML ≠ first client render) — the first client render must equal the server HTML. *No `Date.now`/`Math.random`/`window` in render; use effects, `useId`, or props from the server.* *(advanced)*
- **RSC** (React Server Components) — smaller bundles and colocated data fetching. *Price: a two-environment model, framework lock-in, and one stray `"use client"` at the top pulling everything in.* *(advanced)*
- **Micro-frontends** — solve organizational scaling, not performance. *Try a modular monorepo + feature flags first; share React as a singleton.* *(advanced)*

### Data and state management

> **Start here:** server data goes in React Query/SWR, not in your own `useState`; use a query key that lists every input.

- **Server state ≠ client state** — use React Query/SWR for fetched data (caching, revalidation). *For genuine client state use Context+`useReducer` or Zustand/Redux, chosen by scale and update frequency.*
- **Query keys** — the cache identity + fetch dependencies, e.g. `["user", id]`. *Include every input, structure hierarchically, invalidate by prefix after mutations.*
- **`staleTime` vs `gcTime`** — staleTime = how long data counts as fresh; gcTime = how long unused data stays in cache.
- **Optimistic updates** — show the result before the server confirms. *Cancel in-flight queries, snapshot, roll back on error, invalidate on settle; disable duplicates and make mutations idempotent.*
- **React 19** — Actions (`<form action>`), `useActionState`, `useOptimistic`, `use(promise)`. *Optimistic state is transient (await the mutation inside the action); the promise passed to `use` must be stable.* *(advanced)*

### TypeScript

> **Start here:** prefer `unknown` to `any`, model states as unions, and validate outside data at runtime.

- **`interface` vs `type`** — interface for extendable object shapes; type for unions/intersections/mapped types.
- **Discriminated union** — a union with a shared tag field, e.g. `{status:"loading"} | {status:"ok", data:T}`. *Beats a "boolean soup" (`isLoading`, `isError`…): invalid state combinations become unrepresentable, not just avoided by convention.*
- **`unknown` vs `any`** — `any` disables checking; `unknown` forces narrowing/validation before use. *Always prefer `unknown` at trust boundaries.*
- **External data** — validate at the boundary (Zod or equivalent). *A compile-time-only `as T` assertion enforces nothing at runtime.*
- **`as const` / `satisfies` / `never`** — `as const` keeps literals, `satisfies` validates shape without widening, `never` gives a compile error when a union member is unhandled. *Prefer literal unions over `enum`.* *(advanced)*
- **Polymorphic components** — generic `C extends ElementType` with `Omit<ComponentProps<C>, keyof Own>`. *Restrict `as` for accessibility or prefer `asChild`/separate components.* *(advanced)*

### Testing

- **Test behavior, not implementation** — query by role/text/label and interact like a user. *Implementation-detail tests break on valid refactors.*
