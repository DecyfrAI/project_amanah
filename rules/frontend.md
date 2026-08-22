# Frontend Engineering Rules

Framework-neutral rules for TypeScript-first, component-based frontend applications. Terminology follows [RFC 2119](https://tools.ietf.org/html/rfc2119): **MUST** (required), **SHOULD** (recommended unless there is a specific reason not to), **MAY** (optional).

---

## Components

- Components MUST have a single, clearly defined responsibility. A component that fetches data, formats it, and renders a complex layout is three components.
- One stateful component SHOULD live per file. Multiple co-located pure/presentational sub-components MAY share a file when they are only used by their parent.
- Component filenames and export names MUST use `PascalCase`.
- Components MUST be implemented as functions, not classes, unless lifecycle methods unavailable to hooks are strictly required.
- Components SHOULD be kept small enough to be read in full in one screen. Extract when a component exceeds ~150 lines.
- Higher-order components or wrapper components MUST set a descriptive `displayName` that reflects the composition, e.g. `withAuth(UserProfile)`.
- Components MUST NOT inherit from other components. Prefer composition.
- Avoid complex conditional logic inside component render output. Extract branches into named variables or sub-components.

```tsx
// bad — mixed concerns, hard to test in isolation
function UserDashboard({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => { fetchUser(userId).then(setUser); }, [userId]);
  if (!user) return <Spinner />;
  return (
    <div>
      <h1>{user.name}</h1>
      <ul>{user.roles.map(r => <li key={r}>{r}</li>)}</ul>
    </div>
  );
}

// good — data concern separated from presentation
function UserDashboard({ userId }: { userId: string }) {
  const { data: user, isLoading } = useUser(userId);
  if (isLoading) return <Spinner />;
  if (!user) return null;
  return <UserProfile user={user} />;
}

function UserProfile({ user }: { user: User }) {
  return (
    <div>
      <h1>{user.name}</h1>
      <RoleList roles={user.roles} />
    </div>
  );
}
```

---

## State Management

- State MUST live at the lowest component in the tree that needs it. Do not hoist state higher than necessary.
- Shared state SHOULD be managed via context before reaching for a global state library.
- Custom hooks MUST encapsulate stateful logic that is reused across more than one component.
- State that derives from other state MUST NOT be duplicated in a second state variable — compute it inline or with `useMemo`.
- Global state libraries MAY be used when context performance limitations become measurable, not as a default architectural choice.
- Avoid storing UI-only state (hover, focus, open/close) in global state.

```tsx
// bad — derived state duplicated
const [items, setItems] = useState<Item[]>([]);
const [count, setCount] = useState(0); // duplicates items.length

// good — derived inline
const [items, setItems] = useState<Item[]>([]);
const count = items.length;
```

---

## Props

- All component props MUST be typed via a TypeScript `interface` or `type`. Do not use runtime-only prop-types libraries when TypeScript is available.
- Prop names MUST use `camelCase`. Props whose values are component types MUST use `PascalCase`.
- Boolean props SHOULD be written without a value when the value is `true`.
- Props MUST NOT shadow native DOM attribute names (`style`, `className`, `onClick`) with semantically different values.
- Avoid using array index as a `key` prop. Keys MUST be stable, unique identifiers tied to the data item.
- Spread props (`{...props}`) SHOULD be avoided on leaf DOM elements. When a HOC must forward props, filter irrelevant ones before spreading.
- Optional props SHOULD use the `?` optional modifier rather than typing them as `T | undefined`.
- Props interfaces SHOULD be co-located with their component and exported when consumers need to extend them.

```tsx
// bad
interface CardProps {
  style: string;           // shadows DOM attribute
  isVisible: boolean;
  items: any[];            // untyped
}

// good
interface CardProps {
  variant: 'outlined' | 'elevated';
  isVisible?: boolean;
  items: CardItem[];
}

// bad
<Tooltip visible={true} />

// good
<Tooltip visible />

// bad — index key causes reconciliation bugs on reorder
{items.map((item, i) => <Row key={i} item={item} />)}

// good
{items.map(item => <Row key={item.id} item={item} />)}
```

---

## Accessibility

- Every interactive element (button, link, input, custom control) MUST have an accessible name. Prefer visible text labels; use `aria-label` or `aria-labelledby` only when visible text is not feasible.
- Semantic HTML MUST be used as the foundation. Do not replace `<button>` with `<div role="button">` when a `<button>` works. Do not replace `<a href>` with a click-handled `<span>`.
- `<img>` elements MUST include an `alt` attribute. Decorative images MUST use `alt=""`. Alt text MUST NOT begin with "image of" or "picture of" — screen readers already announce the element type.
- ARIA roles MUST be valid, non-abstract WAI-ARIA roles. Do not invent roles.
- `accessKey` MUST NOT be used — it conflicts with screen reader and OS shortcuts.
- All interactive content MUST be keyboard-operable. Tab order MUST follow the visual reading order.
- Focus MUST be trapped inside modals and dialogs while they are open, and restored to the trigger element on close.
- Form inputs MUST be programmatically associated with a visible `<label>` via `for`/`id` or wrapping. Placeholder text MUST NOT be used as a substitute for a label.
- Related inputs (radio groups, checkboxes) MUST be grouped with `<fieldset>` and labelled with `<legend>`.
- Error messages MUST be programmatically associated with their input using `aria-describedby`.
- Dynamic content changes MUST be announced to assistive technology via live regions (`aria-live`) or focus management.
- Foreground/background color pairs MUST meet WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text).
- Color MUST NOT be the only visual cue conveying meaning.
- Animation MUST NOT auto-play indefinitely and MUST respect `prefers-reduced-motion`.
- Each page or view MUST have a unique, descriptive `<title>`.
- Heading levels MUST NOT be skipped (e.g., jumping from `<h1>` to `<h3>`).
- Interactive target sizes SHOULD meet WCAG 2.5.8 minimum (24×24 CSS pixels), with adequate spacing between grouped controls.

```tsx
// bad
<div onClick={handleClose}>✕</div>

// good
<button type="button" aria-label="Close dialog" onClick={handleClose}>
  <CloseIcon aria-hidden="true" />
</button>

// bad
<input placeholder="Email address" />

// good
<label htmlFor="email">Email address</label>
<input id="email" type="email" aria-describedby="email-error" />
{error && <span id="email-error" role="alert">{error}</span>}
```

---

## Styling

- Colors, typography scales, spacing units, and breakpoints MUST be defined in a central theme/token system, not hardcoded in component styles.
- CSS class names SHOULD follow a consistent convention across the project (e.g., BEM or utility classes). The convention MUST be documented and applied uniformly — do not mix methodologies in the same project.
- ID selectors MUST NOT be used for styling.
- Selector specificity SHOULD be kept as low as possible. Avoid over-qualified selectors such as `div.card-title`.
- Inline styles SHOULD only be used for values that vary at runtime (e.g., a width derived from a prop). Static styles MUST live in a class or style object, not inline.
- Breakpoint names MUST use device-agnostic vocabulary (`small`, `medium`, `large`) rather than device names (`mobile`, `tablet`, `desktop`).
- CSS-in-JS style objects MUST use camelCase keys. Modifier styles SHOULD follow a `baseName_modifier` naming pattern.
- Avoid nesting selectors more than 3 levels deep.
- Viewport zooming MUST NOT be disabled via `user-scalable=no`.

```tsx
// bad — hardcoded values bypass the token system
const styles = { color: '#bada55', fontSize: '14px' };

// good — values come from the theme
const styles = { color: theme.color.accent, fontSize: theme.text.sm };

// bad — device-named breakpoints
const breakpoints = { mobile: '(max-width: 639px)' };

// good
const breakpoints = { small: '(max-width: 639px)' };
```

---

## Performance

- Expensive computations MUST be memoized with an appropriate primitive (`useMemo`, computed properties) and MUST NOT be inlined in render without measurement showing it is cheap.
- Callback references passed as props to pure/memoized child components SHOULD be stabilized (e.g., `useCallback`) to prevent unnecessary re-renders.
- Arrow functions defined inside render MUST NOT be passed to `PureComponent`-equivalent children as the sole optimization — they create a new reference on every render.
- Lists MUST NOT use array index as `key`; doing so defeats reconciliation optimizations when items reorder or are deleted.
- Images MUST specify `width` and `height` attributes or CSS dimensions to eliminate layout shift (CLS).
- Images SHOULD use modern formats (WebP, AVIF) with appropriate fallbacks, and SHOULD be loaded lazily below the fold via `loading="lazy"`.
- Synchronous scripts MUST NOT block the critical rendering path. Use `defer` or `async` for non-critical scripts.
- DOM depth SHOULD be minimized. Parent elements SHOULD NOT contain more than 60 direct children (Lighthouse recommendation).
- Avoid forcing a re-render of the entire component tree when only a leaf changes. Use granular subscriptions or state scoping.
- Assets (fonts, images, critical CSS) SHOULD be preloaded when they are needed immediately on page load.

```tsx
// bad — new function reference every render defeats React.memo
function List({ items, onSelect }: Props) {
  return (
    <MemoizedRow
      items={items}
      onSelect={(id) => onSelect(id)}   // new ref every render
    />
  );
}

// good
function List({ items, onSelect }: Props) {
  const handleSelect = useCallback((id: string) => onSelect(id), [onSelect]);
  return <MemoizedRow items={items} onSelect={handleSelect} />;
}
```

---

## Data Fetching

- Data fetching logic MUST NOT live directly inside view components. Extract it into a custom hook or a dedicated data layer.
- Components MUST handle all three fetch states: loading, error, and success. None may be silently ignored.
- Fetch requests MUST be cancelled or ignored on component unmount to prevent setting state on an unmounted component.
- API calls SHOULD be deduplicated — avoid triggering the same request from multiple sibling components. Hoist the call to a common ancestor or use a caching/query library.
- Loading and error UI MUST be rendered at a level that gives the user actionable feedback without destroying unrelated UI.
- Pagination, infinite scroll, and background refetch logic SHOULD be implemented via a data-fetching library rather than bespoke `useEffect` chains.

```tsx
// bad — fetch logic inside component, no cleanup, missing error handling
function UserCard({ id }: { id: string }) {
  const [user, setUser] = useState<User>();
  useEffect(() => {
    fetch(`/api/users/${id}`).then(r => r.json()).then(setUser);
  }, [id]);
  return user ? <div>{user.name}</div> : null;
}

// good — extracted hook, cleanup, all states handled
function useUser(id: string) {
  const [state, setState] = useState<{ data?: User; error?: Error; loading: boolean }>({
    loading: true,
  });
  useEffect(() => {
    let cancelled = false;
    setState({ loading: true });
    fetchUser(id)
      .then(data => { if (!cancelled) setState({ data, loading: false }); })
      .catch(error => { if (!cancelled) setState({ error, loading: false }); });
    return () => { cancelled = true; };
  }, [id]);
  return state;
}
```

---

## Forms

- Every form input MUST have a programmatically associated, visible label.
- Form validation MUST surface errors inline, adjacent to the relevant field, and programmatically associated via `aria-describedby`.
- Submit buttons MUST use `type="submit"` inside a `<form>`. Action-only buttons outside a form MUST use `type="button"` to prevent implicit form submission.
- Forms SHOULD use uncontrolled inputs managed by a form library for large, complex forms to avoid per-keystroke re-renders.
- Required fields MUST be communicated both visually and programmatically (`required`/`aria-required`).
- Validation SHOULD run on blur for individual fields and on submit for the full form. Avoid real-time validation before the user has finished typing.
- Passwords and sensitive fields MUST NOT be autocompleted unless explicitly appropriate (`autocomplete="current-password"`).

```tsx
// bad — label not associated, no error feedback
<input placeholder="Email" onChange={handleChange} />

// good
<div>
  <label htmlFor="email">
    Email <span aria-hidden="true">*</span>
  </label>
  <input
    id="email"
    type="email"
    required
    aria-required="true"
    aria-describedby={emailError ? 'email-error' : undefined}
    value={email}
    onChange={e => setEmail(e.target.value)}
  />
  {emailError && (
    <span id="email-error" role="alert">
      {emailError}
    </span>
  )}
</div>
```

---

## Error States

- Components that fetch data or perform async operations MUST render a meaningful error state, not a blank screen.
- Error boundaries MUST be placed at meaningful subtree boundaries so that a single component failure does not crash the entire page.
- Error messages shown to users MUST be actionable (e.g., "Try again" button) and MUST NOT expose raw error objects, stack traces, or internal system details.
- Network errors and expected failure modes (404, 403, validation failures) MUST be handled explicitly and SHOULD NOT fall through to the generic error boundary.
- Error state UI SHOULD maintain the surrounding layout so the user understands what part of the page failed.

```tsx
// bad — no feedback to the user
if (error) return null;

// good
if (error) {
  return (
    <div role="alert">
      <p>Failed to load your profile.</p>
      <button type="button" onClick={retry}>Try again</button>
    </div>
  );
}
```

---

## Loading States

- Every async operation that affects visible UI MUST show a loading indicator while in-flight. Silent loading is not acceptable.
- Skeleton screens SHOULD be preferred over spinners for content that has a predictable shape, to reduce perceived latency and layout shift.
- Loading indicators MUST be accessible: spinners MUST include an `aria-label` or a visually hidden text description. Live regions (`aria-live="polite"`) SHOULD announce completion.
- Buttons that trigger async actions SHOULD be disabled and show a loading state during the operation to prevent duplicate submissions.
- Loading states MUST NOT break keyboard navigation or trap focus unexpectedly.

```tsx
// bad — spinner with no accessible label
{isLoading && <Spinner />}

// good
{isLoading && (
  <div role="status" aria-label="Loading user profile">
    <Spinner aria-hidden="true" />
  </div>
)}

// good — async button
<button
  type="submit"
  disabled={isSaving}
  aria-busy={isSaving}
>
  {isSaving ? 'Saving…' : 'Save'}
</button>
```

---

## Responsive Design

- Layouts MUST be designed mobile-first using `min-width` media queries, progressively enhancing for larger viewports.
- Breakpoints MUST be defined in terms of content needs, not specific device dimensions.
- Breakpoint values SHOULD use `em` units so that user font-size preferences are respected.
- Viewport zooming MUST NOT be disabled. The `meta viewport` tag MUST NOT include `user-scalable=no` or `maximum-scale=1`.
- Content MUST reflow and remain readable when the viewport is zoomed to 400% without horizontal scrolling (WCAG 1.4.10 Reflow).
- Touch targets MUST meet minimum size requirements (WCAG 2.5.8: 24×24 CSS pixels minimum, 44×44 recommended).
- Images and media MUST use responsive techniques (`max-width: 100%`, `srcset`, `<picture>`) to avoid overflow on small screens.
- Avoid relying on `hover`-only interactions for essential functionality — touch devices have no hover state.

```scss
// bad — device-specific breakpoints
@media (max-width: 375px) { … }

// good — content-driven, em-based, mobile-first
.card-grid {
  display: grid;
  grid-template-columns: 1fr;

  @media (min-width: 40em) {        // ~640px at 16px base
    grid-template-columns: repeat(2, 1fr);
  }

  @media (min-width: 64em) {        // ~1024px
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## Code Splitting

- Route-level code splitting MUST be applied so that each page loads only the JavaScript it requires. Monolithic bundles that load the entire app upfront are not acceptable in production.
- Dynamic imports MUST be used for large, conditionally rendered features (modals, rich editors, chart libraries) that are not needed on initial paint.
- Split boundaries MUST be wrapped with a Suspense boundary (or equivalent) that renders a meaningful fallback during the load.
- Third-party libraries with large footprints SHOULD be loaded dynamically and deferred unless they are required for above-the-fold content.
- Code splitting decisions SHOULD be validated with bundle analysis tooling (e.g., source-map-explorer, bundle analyzer plugin) rather than assumed.
- Prefetch hints MAY be added for routes or chunks that the user is likely to navigate to next, to mask the latency of a split.

```tsx
// bad — entire route tree in one bundle
import AdminPanel from './AdminPanel';

// good — AdminPanel is only loaded when the route is visited
const AdminPanel = lazy(() => import('./AdminPanel'));

function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Suspense>
  );
}
```
