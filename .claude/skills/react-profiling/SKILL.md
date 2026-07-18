---
name: react-profiling
description: Profile React app rendering, commit duration, component re-render frequency, interaction latency, and browser trace correlation with React DevTools and React Profiler APIs.
---

# React Performance Profiling Skill

Use this skill when a React application's render behavior, commit duration, component re-render frequency, or interaction latency needs evidence. Choose the smallest profiler that answers the question, and keep React render evidence separate from browser layout, paint, network, and GPU evidence.

## Choose the evidence

| Question | First evidence | Why | Boundary |
| --- | --- | --- | --- |
| Which components re-render, how often, and why during an interaction? | React DevTools Profiler | Interactive commit timings and component render attribution | React render attribution does not explain network, layout, paint, or browser scheduling by itself |
| How long does a specific React subtree render across commits in code? | React `<Profiler id="..." onRender={...}>` | Programmatic measurements for commits in the wrapped subtree | Measures React render commits for that subtree, not network, layout, paint, or GPU work |
| Is load, interaction, layout, or paint work causing the user-visible delay? | Chrome DevTools Performance trace | Correlates scripting, tasks, layout, paint, network, and user interactions on the browser timeline | Browser traces do not automatically identify which React component caused a render |

## React DevTools Profiler workflow

Use React DevTools Profiler as the interactive tool for commit timings and component render attribution.

1. Reproduce the scenario in the same build, route, data state, viewport, and browser settings that users exercise. Prefer a production profiling build when the project supports one; development-only diagnostics can change render cost.
2. Open React DevTools Profiler, start recording immediately before the interaction, perform only the bounded scenario, and stop promptly.
3. Inspect commits in order. Record commit duration, the selected interaction or state change, components that rendered, and whether the render was mount or update work.
4. Use component render attribution to form a hypothesis: unnecessary parent state changes, unstable props, context updates, expensive render functions, or a subtree that should be memoized. Verify the cause in code before recommending a change.
5. Repeat the same scenario after a proposed fix and compare the same commit window. Do not compare a cold first render with a warmed interaction commit.

## Programmatic <Profiler> measurements

Wrap the smallest subtree that matches the question:

```jsx
<Profiler id="App" onRender={onRender}>
  <App />
</Profiler>
```

React `<Profiler>` requires `id` and `onRender`. It measures commits for the wrapped subtree and calls `onRender` when components within that tree commit an update. Use it for render measurements, not network, layout, paint, or GPU attribution.

Keep `onRender` lightweight and record enough context to compare like with like: profiler `id`, commit phase, actual duration, base duration, start time, commit time, interaction label, input size, route, and build. Avoid logging user data, props, or application state unless the data-handling policy explicitly permits it.

## Correlate React commits with browser traces

React render time is only one part of user-visible latency. When the question involves load, input delay, animation jank, layout, paint, network, or browser scheduling, capture a Chrome DevTools Performance trace for the same scenario.

Use User Timing marks or a stable interaction label to align the React commit window with the browser trace. Then compare React commits with main-thread tasks, event dispatch, style/layout, paint, network completion, and garbage collection. A long React commit can cause a slow interaction, but a slow interaction can also be dominated by network wait, layout, paint, hydration, or unrelated JavaScript.

## Reporting and limits

Report the React version, build mode, route/screen, input data shape, browser, viewport, recording workflow, number of comparable runs, selected commits, component evidence, and the browser trace interval when one was used.

Do not present React DevTools Profiler output as a complete browser Performance trace. Do not present `<Profiler>` measurements as proof of layout, paint, network, memory retention, or GPU cost. Every optimization claim needs the same scenario measured before and after the change.