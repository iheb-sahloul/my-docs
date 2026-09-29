# React & TypeScript Best Practices



## 🔷 TypeScript

### Turn on `strict` mode
Set `"strict": true` in `tsconfig.json`, and add `noUncheckedIndexedAccess` if you can.

**Why it's a best practice:** without `strict`, `null` and `undefined` are accepted everywhere and untyped
parameters silently become `any`, so the compiler misses exactly the bugs you use TypeScript for ("cannot read
properties of undefined"). `noUncheckedIndexedAccess` types `arr[i]` and `record[key]` as possibly `undefined`,
which they are. Turning it on late is painful, so start with it.

✅ `{ "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true } }`

### Use `unknown`, not `any`
Type values you don't know yet (API responses, `JSON.parse`, `catch` errors) as `unknown`, and narrow them before
use.

**Why it's a best practice:** `any` turns off type checking, and it spreads: anything derived from an `any` is
`any` too. `unknown` accepts every value but lets you do nothing with it until you check its type, so the
compiler forces the validation. For external data, validate with a schema library (zod, valibot) that gives you
the type and the runtime check at once.

```ts
// ⛔ no error until it crashes at runtime
const user: any = await res.json();
user.profile.name.toUpperCase();

// ✅ validated at the boundary
const User = z.object({ name: z.string() });
const user = User.parse(await res.json());
```

### Model state with discriminated unions
Represent states that exclude each other as a union with a `status` (or `kind`) field, not as several optional
booleans.

**Why it's a best practice:** `{ isLoading: boolean; error?: Error; data?: User }` allows impossible
combinations: loading *and* error, or neither loading nor data. Every component has to guess which one wins. A
discriminated union makes invalid states unrepresentable, and TypeScript narrows the type in each branch: `data`
only exists when `status === 'success'`.

```ts
// ⛔ 8 combinations, 3 valid
type State = { isLoading: boolean; error?: Error; data?: User };

// ✅
type State =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: User };
```

### Use `satisfies` and `as const` instead of `as`
Check a value against a type with `satisfies`, and freeze literal values with `as const`. Avoid `as` casts.

**Why it's a best practice:** `value as User` tells the compiler to trust you, even when the value is missing
fields: the error moves to runtime. `satisfies` checks the value against the type but keeps its more precise
inferred type. `as const` keeps literal types (`'admin'` instead of `string`) and makes the object readonly, which
lets you derive union types from a single source of truth.

```ts
// ⛔ compiles even though `path` is missing
const route = { name: 'home' } as Route;

// ✅
const ROLES = ['admin', 'editor', 'viewer'] as const;
type Role = (typeof ROLES)[number]; // 'admin' | 'editor' | 'viewer'
const config = { port: 3000 } satisfies Config;
```

## ⚛️ State & rendering

### Derive values instead of syncing them with `useEffect`
If a value can be computed from props or state, compute it during render. Don't store it in another state and
update it in an effect.

**Why it's a best practice:** syncing with an effect renders twice (once with the stale value, then again after
the effect), and the two states can get out of sync when one update path is forgotten. A value computed during
render is always correct. If the computation is really expensive, wrap it in `useMemo`, still without extra
state.

```tsx
// ⛔ extra render, can drift
const [fullName, setFullName] = useState('');
useEffect(() => setFullName(`${first} ${last}`), [first, last]);

// ✅
const fullName = `${first} ${last}`;
```

### Never mutate state
Always create a new object or array when updating state.

**Why it's a best practice:** React compares state by reference. If you `push` into the existing array and call
`setItems(items)`, the reference hasn't changed, so React skips the re-render and the UI shows stale data.
Memoized children and effects that depend on the value miss the change too. Use spread, `map`, `filter`, or
`toSorted` / `toSpliced`, which return new arrays.

```tsx
// ⛔ same reference, no re-render
items.push(newItem);
setItems(items);

// ✅
setItems(prev => [...prev, newItem]);
```

### Use stable, unique `key`s in lists
Use an id from the data as `key`, not the array index.

**Why it's a best practice:** React uses the key to match elements between renders. With the index, removing
or reordering an item shifts the keys, so React reuses the wrong component instance: input values, focus and
local state jump to the wrong row. A stable id keeps each component attached to its item. The index is only safe
for static lists that never change order.

⛔ `items.map((item, i) => <Row key={i} item={item} />)`

✅ `items.map(item => <Row key={item.id} item={item} />)`

### Declare every effect dependency and clean up
List everything the effect uses in the dependency array (let the `react-hooks/exhaustive-deps` lint rule do it),
and return a cleanup function for subscriptions, timers and requests.

**Why it's a best practice:** a missing dependency means the effect keeps using the value from the first render
(a stale closure): it fetches the old id or sends the old filter. Without cleanup, timers and listeners pile up
on each re-render or remount, and a slow response can arrive after a newer one and overwrite it. In development,
React Strict Mode mounts components twice to reveal missing cleanups.

```tsx
// ✅ ignore stale responses
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/users/${id}`, { signal: controller.signal }).then(/* ... */);
  return () => controller.abort();
}, [id]);
```

### Use a data-fetching library for server state
Fetch server data with TanStack Query (or SWR, or your framework's loaders) instead of `useState` + `useEffect`.

**Why it's a best practice:** hand-written fetching in effects has to handle loading and error states, race
conditions, caching, deduplication, retries and refetching after a mutation, and each component ends up doing it
a bit differently. These libraries do all of that, share the cache between components, and keep the UI in sync
with the server. Keep `useState` for real UI state (an open modal, a form input).

```tsx
// ✅
const { data, isPending, error } = useQuery({
  queryKey: ['user', id],
  queryFn: () => fetchUser(id),
});
```

### Memoize only when you've measured a problem
Don't wrap every value in `useMemo` and every function in `useCallback` by default.

**Why it's a best practice:** memoization isn't free: it costs memory, a dependency comparison on every render,
and readability. It only helps when the computation is really expensive, or when the value is passed to a
`memo` component or used as an effect dependency. Use the React DevTools profiler to find slow renders first. The
React Compiler memoizes automatically, which makes most manual cases unnecessary.

⛔ `` const label = useMemo(() => `Hello ${name}`, [name]); ``
✅ `` const label = `Hello ${name}`; ``

## 🧩 Components

### Keep components small and extract custom hooks
One component, one job. Move stateful logic (fetching, subscriptions, form handling) into custom hooks.

**Why it's a best practice:** a 500-line component mixing data fetching, business rules and markup is hard to
read, re-renders as a whole, and can't be tested in parts. A custom hook (`useCart()`) gives the logic a name,
can be reused by several components and tested on its own. Presentational components that only take props are
easy to reuse and to show in Storybook.

⛔ a `CheckoutPage` with 12 `useState`s and 4 `useEffect`s
✅ `const cart = useCart(); const payment = usePayment();` + `<CartSummary cart={cart} />`

### Type props explicitly and avoid prop drilling
Declare a `Props` type for each component. When the same prop is passed through 3+ levels, use composition
(`children`) or a context.

**Why it's a best practice:** explicit prop types document the component's API and catch wrong usage at every
call site. Passing a prop through components that don't use it couples all of them: renaming it touches every
level. Passing already-built elements as `children` often removes the need for context. Keep context for truly
global values (theme, current user), since every consumer re-renders when it changes.

```tsx
// ✅
type ButtonProps = { variant: 'primary' | 'secondary'; onClick: () => void; children: React.ReactNode };
function Button({ variant, onClick, children }: ButtonProps) { /* ... */ }
```

## ♿ Forms & accessibility

### Use semantic HTML
Use `<button>` for actions, `<a href>` for navigation, `<label>` for inputs, and headings in order.

**Why it's a best practice:** a `<div onClick>` can't be reached with the keyboard, isn't announced as a button
by screen readers, and doesn't respond to Enter or Space. You'd have to rebuild all of that by hand with `role`,
`tabIndex` and key handlers. Native elements get it for free. An input without a `<label>` is unnamed for
assistive technology, and clicking the label no longer focuses the input.

⛔ `<div onClick={save}>Save</div>`, `<input placeholder="Email" />`
✅ `<button type="button" onClick={save}>Save</button>`, `<label>Email <input type="email" /></label>`

### Validate forms with a schema
Use a form library (React Hook Form) with a schema (zod) instead of ad-hoc checks in `onChange` handlers.

**Why it's a best practice:** hand-written validation is scattered and inconsistent, and the rules often
differ between the client and the server. A schema declares all rules in one place, gives you the TypeScript type
of the form values, and can be shared with the backend. Client validation is only for user experience: the
server must validate again, since any client can bypass it.

```tsx
// ✅
const schema = z.object({ email: z.string().email(), age: z.number().int().min(18) });
type FormValues = z.infer<typeof schema>;
const form = useForm<FormValues>({ resolver: zodResolver(schema) });
```
