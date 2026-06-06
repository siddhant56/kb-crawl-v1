# A Perfect Guide to useEffect Hook in React

> Here is a complete guide to useEffect hook in React with a detailed discussion of its advantages, side-effects, use case and code examples

**Source:** https://radixweb.com/blog/guide-to-useeffect-hook-in-react

---

Web App Development

# A Complete Guide to useEffect Hook in React with Code Examples

Dhaval Dave

Updated : May 14, 2026

 _**Quick Rundown:**_ _Have you ever been overwhelmed by the complexities of React state management? It’s time to relax because useEffect is here to ease the complexity. This powerful React Hook has revolutionized the way React developers build dynamic applications. In this comprehensive guide, we will explore its intricacies, from basic usage to advanced techniques. Read on to elevate your React development with the power of useEffect._

If you are a front-end developer, or more precisely, a ReactJS developer (novice or experienced), you may find it challenging to understand hooks in React. Because hooks in React require an understanding of a few unfamiliar programming concepts.

And since the release of React 16.8, hooks have become the newest addition and powerful tool for React developers.

One of the challenging and trickiest hooks I find myself using all the time is `useEffect` in React.

The `useEffect` hook is the Swiss Army Knife of all the hooks available. It’s the finest solution to all problems, like:

  1. How to execute code when state or prop changes,

  2. How to configure timers or intervals,

  3. How to fetch data when a component mounts, and many more.

As a result, understanding how React `useEffect` Hooks works and when to use it are the most important concepts for mastering React today.

I have been working with React for several years now. And currently, I am using the latest version – React 18, with a new feature - Strict Mode. So, for me, it’s essential to know how utilizing `useEffect` differs from working with the lifecycle methods of class-based components. React `useEffect` allows you to perform side effects in your functional components.

Well, I know it’s not easy to understand issues of effects. And that’s why one of the team members of React, Dan Abramov stated that you might have to unlearn something to grasp effects completely.

They allow you to use the state and other React functionalities without writing an ES6 class for it. Hence, hooks have made the use of functional components easier than class-based components. That’s the reason that has astounded the entire React community.

Avid developers like me, and you are curious to learn how does `useEffect` works and how to use `useEffect` to enhance their React app development skills. Actually, React.js is the perfect choice for enterprises and developers to deliver better productivity, customer satisfaction, and work efficiency.

So, without any further ado, let’s discuss the existence of this hook and how to use it properly in your React projects today. The primary objective of this article is to gather information about the fundamentals of `useEffect` and share my learning experience with React `useEffect` Hook.

On This Page

  1. What is React Hook?
  2. Advantages of React Hooks
  3. What is React `useEffect`?
  4. What are Side-effects in React?
  5. Concepts of `useEffect` in React
  6. How to Use React `useEffect` Hook?
  7. What is `useEffect` Cleanup Function?
  8. How to Use `useEffect` instead of React’s Lifecycle Functions?
  9. When to Use the `useEffect` Hook?
  10. What’s Next Now?

## What is React Hook?

React offers Functional Components that don’t consider internal state and Class Components that add stateful logic to the program. This actually enables you to use React hooks lifecycle methods.

Initially, many developers were unhappy with this approach, as Class Components require ES6 classes to maintain internal states. However, I was unhappy too.

But React comes with an alternative – React Hooks.

React Hooks are functions that allow you to hook into React state and lifecycle features from function components. You can use React without classes, which are generally not preferred due to their need for JavaScript these calls. The best part is, Hooks can easily integrate with existing code.

You will come across several built-in Hooks, like `useEffect` or `useState` that refer to frequent internal states. Moreover, React allows you to create custom Hooks of your specific states as well.

Three popular built-in Hooks are:

`useState`: It returns a stateful value and a function to edit it. You can consider it as the Hook of `this.state` and `this.setState` in Class Components.

`useEffect`: It performs side effects from function components. These are put in a queue after a re-render to support React's limited iterative behavior.

`useContext`: The goal of `useContext` is to accept a context object and return the existing context value. It causes a re-render next time when there’s an update for `MyContext.Provider`.

## Advantages of React Hooks

### Simplified State and Lifecycle Management

React Hooks allow developers to manage state and lifecycle behavior within functional components using APIs like use State and use Effect. This removes the need for class-based components and eliminates the complexity of handling these bindings.

### Improved Code Reusability

Hooks enable logic reuse without relying on higher-order components (HOCs) or render props. Custom hooks allow teams to extract and share business logic across components in a clean, modular way, improving consistency and reducing duplication across large React applications.

### Cleaner and More Maintainable Code Structure

By grouping related logic together instead of splitting it across lifecycle methods, hooks make components more structured. This leads to better readability, especially in complex applications where multiple side effects and state dependencies must be managed simultaneously.

### Better Separation of Concerns

Hooks allow developers to isolate different concerns such as data fetching, subscriptions, or DOM manipulation into separate functions. This results in components that are easier to test, debug, and scale over time.

### Enhanced Performance Optimization

Hooks like use Memo and use Callback help optimize performance by memorizing values and functions. This reduces unnecessary re-renders and improves efficiency in applications with complex UI interactions or large datasets.

### Reduced Boilerplate Code

Functional components with hooks typically require less code compared to class components. There is no need for constructors, lifecycle methods, or verbose state management patterns.

### Easier Testing and Debugging

Since hooks encourage smaller, function-based logic units, testing becomes more straightforward. Developers can isolate and validate specific behaviors without dealing with complex component hierarchies.

### Seamless Integration with Modern React Ecosystem

Hooks are the standard approach in modern React development. They integrate well with libraries, state management tools, and modern patterns such as functional programming and component-driven architecture for long-term compatibility and scalability.

## What is React `useEffect`?

In 2018, there was some addition to the library in core React Hooks (`useEffect`, `useState`, and many more). In the end, many developers, including myself, were confused with terminology and usage of this hook – “`useEffect`”.

And I also don’t want you to get confused with the term. Hence, I will explain what exactly an “effect” and “`useEffect`” are in React.

### React `useEffect`

React `useEffect` is one of the most renowned hooks of React, allowing you to perform side effects in function components throughout the application development. The primary goal of `useEffect` Hook is to execute additional code once React updates the DOM.

However, in the React Hooks era, it’s essential to understand that you can easily invoke effects from within functional components with the help of `useEffect` in React. In fact, you may find it cumbersome at first utilizing the side effects invoked by the `useEffect` Hooks, but eventually, you will get your hands on it.

In addition, a function – React `useEffect` aims to get executed for three various React component lifecycles. You can consider `useEffect` Hook as a partial replacement for React lifecycle events.

React hooks lifecycles are as below:

`componentDidMount`

`componentDidUpdate`

`componentWillUnmount`

In other words, if a component has the `useEffect` Hook, you can react to changes in that component.

### `useEffect` Syntax

The `useEffect` considers two arguments:

`useEffect(() => {`

`// write some code for useEffect example`

`}, [someProp, someState]);`

Callback function – the first argument is executed by default after every render.

Optional Dependency array is the second argument that communicates the Hook to callback only if they find any change in a target state. However, the previous and current state value of each dependency is compared by Hook. Here, the Hook uses the first argument callback if the value doesn't match.

The default callback behavior is overridden by React `useEffect` dependency arrays, ensuring the Hook will ignore everything else in the component scope.

### Use Cases of React `useEffect` Hooks

Let’s go through some common use cases of `useEffect` Hooks in React. However, `useEffect` will be used in the pace of a lifecycle method.

  * Add a button's event listener
  * Data retrieval from the API during component mounting
  * Perform an action when state or props change
  * Clean up event listeners during the time of the component unmounts

### Effect

Now, let’s understand the meaning of “effect”.

Here, the term effect, known as a “side effect”, refers to functional programming.

However, we have to understand the fundamentals of a pure function to learn more about a side effect.

Actually, many React components are considered to be pure functions.

It’s quite strange to consider React components as functions. But the fact is, they are.

Here, a regular React function component is declared like a JavaScript function:

`function MyReactComponent() {}`

Most React components are pure functions. As a result, they get input and come up with a predictable output for JSX.

Just to let you know that the input to JavaScript is considered as **Arguments**. And input to a React component is considered as **Props**.

Let’s go through the `useEffect` example where we are defining the `User` component with the prop `name` declared on it. The prop value is displayed in a header element within the `User`.

`export default function App() {`

`return <User name="Radixweb" />`

`}`

`function User(props) {`

`return <h1>{props.name}</h1>; // Radixweb`

`}`

It is pure because you will always receive the same output with every same input.

In fact, here, your output will always be Radixweb, if you pass `User` a name prop with a “Radixweb” value.

You must be wondering – what’s the reason behind having a name for this?

But allow me to tell you that pure functions come with many perks, like reliability, predictability, and ease of testing.

> #### Are You Looking for Scalable Front-End Development with React for Your Business?
>
> We Can Help

## What are Side-effects in React?

In React.js development, a functional component calculates the output using state and/or props. The calculation that a component performs that doesn’t target the output value, then these calculations are referred to as side-effects.

However, side-effects offer unpredictable results as actions are performed with the “outside world”. It’s recommended to use side-effect when you have to reach outside of your React components to perform some action.

Fetch requests, timer functions like `setTimeout()`, manipulating DOM directly, and others are some common examples of side-effects.

The logic of side-effect and component rendering are independent. Since the body calculates the output or call hooks of the component, it’s not recommended to use side-effects directly in the body of the component.

However, you don’t have control over how the component renders.

`function Greet({ name }) {`

`const message = Namaste, ${name}!; // Calculates output`

`// Bad!`

`document.title = Welcome to ${name}; // Side-effect!`

`return <div>{message}</div>; // Calculates output`

`}`

Now the question is decoupling rendering from the side-effect. Here, `useEffect()` – the hook runs side-effects independently of rendering.

`import { useEffect } from 'react';`

`function Greet({ name }) {`

`const message = Namaste, ${name}!; // Calculates output`

`useEffect(() => {`

`// Good!`

`document.title = Greetings to ${name}; // Side-effect!`

`}, [name]);`

`return <div>{message}</div>; // Calculates output`

`}`

If I explain side-effects with another example in another way, it could be:

If anything is affected outside of the React component, it’s known as a side effect.

### Component

`let x = “ ”`

`x = “Radixweb”`

In the above case, side effects don’t occur. Doesn’t affect anything outside of the component.

`document.title = props.name`

`fetch(/ products/${props.id})`

`.then(res => res.json())`

`.then(setData)`

The above example is from a side effect. Affects something outside of the component.

`return <h1>Welcome to {x}</h1>`

Now we can conclude that React has a special place for side effects. It doesn’t occur during component rendering.

Some of the common side effects are:

  * Requesting to an API for data from the backend server
  * Interaction with browser APIs to use `document` or `window` directly
  * Using unpredictable timing functions like `setInterval` or `setTimeout`

That’s where `useEffect` comes into the picture. Let’s see how it works in the example below, where we have to change the title meta tag to display the company’s name in their browser tab.

`function User({ name }) {`

`document.title = name;`

`// This is a side effect. Don't do this in the component body!\`

`return <h1>{name}</h1>;`

`}`

The rendering of our React component is hampered if a side effect is carried out right in its body. It is best to keep side effects apart from the rendering process. If we need to perform a side effect, it should be done after our component render.

This is what the ideal usage of `useEffect` in React JS.

ReactJs comes up with plenty of developer-friendly tools. But `useEffect` in React JS is a useful tool that enables us to communicate with the outside world without affecting the component's rendering or performance.

## Concepts of `useEffect` in React

_**“I’ve found Hooks to be a very powerful abstraction — possibly a little too powerful. As the saying goes, with great power comes great responsibility.”**_

 _**–Bryan Manuele**_

`useEffect` in React adheres to three major concepts, which are:

  1. Fetching data
  2. Reading from local storage
  3. Registering and deregistering event listeners

The lifecycle methods of class-based components are not the same as React's effects. Also, the level of abstraction is different.

Lifecycle approaches do give components a predictable structure. Compared to effects, the code is more explicit, allowing developers to quickly identify the necessary components (such as `componentDidMount`) for carrying out activities at specific lifecycle phases. (e.g., on `component unmount`).

The `useEffect` Hook encourages concern separation and minimizes code duplication. For instance, the official React documentation demonstrates how to use a single `useEffect` in ReactJs declaration to prevent the duplication of code caused by lifecycle methods.

## How to Use React `useEffect` Hook?

The primary syntax of `useEffect` is:

`// 1. import useEffect`

`import { useEffect } from 'react';`

`function MyComponent() {`

`// 2. call it above the returned JSX`

`// 3. pass two arguments to it: a function and an array`

`useEffect(() => {}, []);`

`// return ...`

`}`

The suitable method to perform the side effect in our `User` component is:

  * Import `useEffect` from “react”
  * Call it above the returned JSX in our component
  * Pass two arguments: a function and an array

`import { useEffect } from 'react';`

`function User({ name }) {`

`useEffect(() => {`

`document.title = name;`

`}, [name]);`

`return <h1>{name}</h1>;`

`}`

A callback function was provided to `useEffect` in React.JS. It will be called once the component completes its rendering. Moreover, we can perform one or more side effects in this function.

The second argument is an array - dependencies array. This array should have all of the values that our side effect relies upon.

We need to include name in the dependencies array in the above example because we are changing the title based on a value in the outer scope. By checking its value, this array will determine whether a variable (in this case, name) has changed between renders.

This is completely feasible, as we want to show the updated name and run our side effect again once the name is changed.

> #### Harness the Features of React to Build Innovative Applications for Your Business
>
> Hire React Experts

## What is `useEffect` Cleanup Function?

The `useEffect` cleanup function is the last step in carrying out side-effects correctly in React.

Our side effects occasionally need to be turned off. For instance, if you use the `setInterval` method to start a countdown timer, that interval won't end until we use the `clearInterval` function.

Use of WebSockets and subscriptions is another example of `useEffect`. When we don’t use a subscription, it needs to be "turned off," and this is what the cleaning function does.

Actually, there’s no need for side effect cleanup in every case. It’s only used when you need to stop a repeated side effect while the component unmounts.

Before the component unmounts or the callback is called again, we can return a function that will be executed:

`React.useEffect(() => {`

`console.log('Welcome to Radixweb!');`

`return () => {`

`console.log('Clean up');`

`};`

`}, [props.userId]);`

Typically, this function is used to clean up the component from the system by canceling network requests or invalidating timers.

When `props.userId` changes, the output for the code above will be as follows:

`Welcome to Radixweb!`

`Clean Up`

`Welcome to Radixweb!`

To clear out any dependencies from the previous execution, the `useEffect` cleanup function will only be used before the `userId` changes.

If it finds empty for the second argument, it will be invoked when the component unmounts.

## How to Use `useEffect` instead of React’s Lifecycle Functions?

The React `useEffect` hook does not attempt to transfer the exact same behavior of all lifecycle functions to functional components.

The possible replacements I am going to showcase to you here might have a slight timing difference. However, the hook provides the capability that, in most circumstances, enables you to replace your lifecycle functions.

Let’s go through that as well in the given topic.

### Use `componentDidMount` in Function Components

Now we need to pass an empty array as the second argument to the `useEffect` hook to simulate the behavior of `componentDidMount`.

`React.useEffect(() => {`

`console.log('Wecome to Radixweb!');`

`}, []);`

When the component is installed, the hook only ever executes the callback once because none of the values in an empty array will ever change.

### Use `componentDidUnmount` in Function Components

Here, we are using `componentDidUnmount` in functional components with a cleanup function.

To accomplish this, we must provide an empty array as the second argument and have the callback function return a function. When the component unmounts, the code inside the function we return will be run.

`React.useEffect(() => {`

`console.log('Welcome to Radixweb!');`

`return () => {`

`console.log('Component unmounts');`

`};`

`}, []);`

Since the component won't be re-rendered, we shouldn't update the state in this function.

### Use `componentDidUpdate` in Function Components

The first example of `useEffects` shows that the callback is executed on each update without a second argument.

If you've used `componentDidUpdate` before, you're undoubtedly used to comparing the most recent props with those from the previous one:

`componentDidUpdate(prevProps) {`

`if (prevProps.userId !== this.props.userId) {`

`this.fetchUser();`

`}`

`}`

This is made simpler by the `useEffect` hook, which gives us the option to select whatever attributes or state changes we want to respond to.

The code above would seem like this in a functional component, which is, in my opinion, considerably simpler to read and write:

`React.useEffect(() => {`

` fetchUser();`

`}, [userId]);`

> #### How to build visual experiences that actually generate value for your users & brand?
>
> Talk to Front-end Experts

## When to Use the `useEffect` Hook?

If you wish to execute some functions at the lifecycle of a component, React `useEffect` hook is useful. For example, `useEffect` hook is the preferred choice if you want to update the UI when a state changes.

In addition, you can define a state on the first load – `componentDidMount` and also clean the state when the component is unmounting – `componentWillUnmount`.

### How to Create Component

Let’s create a component and reuse the button component in the `useState` hook section and merge with `useEffect` hook in React as well.

`import React, { useState } from "react"`

`const Button = () => {`

` const [count, setCount] = useState(0)`

` return <button onClick={() => setCount(count + 1)}>You clicked {count} times</button>;`

`}`

`export default Button`

### Import `useEffect`

Now you need to import `useEffect` at the top of the file to use it. We still need React and `useState`.

`import React, { useState, useEffect } from "react"`

### Define `useEffect`

Now the step is to create a new React `useEffect` just before the return statement in the component. Since we want to update the document title every time the user clicks on the button, it’s required to set the mounting part of the `useEffect` hook.

`useEffect(() => {`

`document.title = Hello, you clicked ${count} times.// This is the mounting part`

`}, [])`

As you can see in the below image, You Clicked 0 times. The initial value count is 0.

Every time you click on the button, the text on the button gets updated instead of the title of the tab. As a result, we must include the count state in the `useEffect` hook's update array. Every time the count is updated, the `useEffect` in React JS will be re-run, updating the document title in our case.

`useEffect(() => {`

`document.title = Hello, you clicked ${count} times.`

`}, [count]) // Add the count state in the array here`

Now, the title of the tab will change each time you click the button to represent how many times you have pressed it.

> _What’s Next Now?__Throughout this article – a guide to`useEffect`, we have understood the primary usage of `useEffect`, how to use the Effect hook in React, along with some examples.__Well, after having almost seven years of experience being afront-end developer and utilizing ReactJS in front-end development projects - personal and client’s projects, I can firmly state that `useEffect` hook in React is a powerful tool, allowing you to perform side effects in function components.__Moreover, if you are a novice front-end developer and planning to create a React app, the first step is tocreate a React application with `create-react-app`. Once you have a basic understanding of developing a React application, you may try your hands with the `useEffect` hook to avoid performance issues in your React application.__In a nutshell, if you follow and implement the instructions I gave in this article, you can effectively manage side effects in your React projects.__Let us know your feedback byconnecting with us. I would surely like to help you if you have any doubts or queries regarding React app development._

Dhaval Dave

LinkedIn

VP – Operations & Delivery

|

18 Years of Experience

Dhaval Dave is the VP of Operations & Delivery at Radixweb with over 18 years of experience in enterprise software engineering and technology operations. He specializes in cloud-native architecture, SDLC optimization, and large-scale engineering delivery. Dhaval leads teams that build scalable, resilient software systems for Global 2000 organizations, ensuring operational excellence through Agile methodologies, DevOps practices, and data-driven engineering strategies.

View All Posts