# Implementing SSR with React for Large eCommerce Apps

> Discover how Radixweb develops SSR with React for large eCommerce apps, optimizing performance without heavy investments in cloud-based middleware.

**Source:** https://radixweb.com/tech-studies/ssr-with-react-for-large-ecommerce-app-development

---

Tech Study

# Defining SSR with React while Developing a Large eCommerce App

Setting up SSR with React is not a cakewalk for eCommerce app development. This tech study illustrates a strategy to achieve performance enhancements without substantial investments in middleware for cloud-based platforms.

At Radixweb, we have been developing eCommerce applications for more than two decades now. Throughout this journey, we've witnessed the evolution of technology stacks – from server-rendered pages with limited JavaScript and CSS to the development of comprehensive JavaScript applications.

The platform we used for our eCommerce site was based on React JS for the front-end. And as we know, configuring SSR (Server Side Rendering) with React is not as easy as you think. You will not find a good overview or starting point.

The process we're discussing has been a part of the ongoing project we are currently working on. Presently, we have a fully working SSR solution that has been in production for almost eight years.

With the advent of React's user-friendly approach to facilitating server-side rendering, this rendering technique has surged in popularity, owing to its undeniable benefits. Hence, that was our primary reason for choosing React.js.

In this case study of ReactJS, we will walk you through:

  * The approach we followed to implement SSR with ReactJS – from knowing nothing about SSR to implementing it in production.
  * The strategy behind choosing React.js and our decision-making.
  * Most important lessons we learned while developing a large eCommerce site with ReactJS.

> #### Simplify Strategies for Unlocking the Potential of Modern Web Development with ReactJS
>
> Let’s Take the Journey Ahead

## Choose the “Architecture” on the First Try

When we were developing an eCommerce app for our client in 2015, we took almost many hours to create a robust and maintainable SSR solution. It was a time-consuming process – learning, experimenting, and implementing.

Hence, as an experienced ReactJS development company, we would like to share our thought process and concrete implementation strategies that will help you reduce your time and effort to a successful SSR implementation.

When it comes to software development, we generally tend to make mistakes in choosing the right architecture on the first try. However, later on, you try things out and constantly improve your code base.

We have learned over these years that keeping things simple while developing an application will help you implement and maintain an SSR solution with ReactJS.

## The Tech Stack We Used

We are only highlighting the relevant technology to make you understand the implementation of SSR with React.js.

  * For backend development, we used Node.js and Express.
  * For frontend development, we used React and Redux.
  * We use webpack to build and execute the app on AWS.

The easiest method to choose the right stack for your project is to follow companies that have already implemented and are successful now. While talking about React, more than 2 billion websites worldwide are built using ReactJS.

Moreover, big giants like Netflix, Instagram, Facebook, Walmart, Uber, Tesla, Salesforce, and New York Times are already using ReactJS as the primary technology.

Hence, it was an obvious reason for us to choose React.js for the front end development of our eCommerce application.

## How We Implemented SSR and React in eCommerce Application

While going for eCommerce app development in 2015 for our client, we had some mid-level expertise in ReactJS technology. However, the project was to re-implement an existing webshop. Our team decided to choose React and Node.js for eCommerce development.

## Choosing Reflux (Prior to the Existence of Redux)

Well, there was a time when the development community was using Flux from scratch. Unfortunately, Redux didn’t exist at the time we developed an eCommerce app. Going into the React ecosystem in-depth, we found a library called Reflux to implement Flux. We thought it could be a good choice for our client’s app. So, we picked that one.

An issue we encountered with Reflux in the context of SSR was its singleton store nature, originally not designed for server-side execution. Consequently, we grappled with problematic scenarios in which parts of the state were shared among users.

Upon discovering Redux, we could not control our excitement of using it. And soon, we migrated most of the code base to Redux.

> #### Implementing SSR and Virtual DOM are Enough Reasons to Switch to ReactJS
>
> Road to React

## Implementing React Technology with Our Expertise

We know, React.js is a JavaScript library for programming reusable UI components for both mobile and web applications. We found React, an emerging tech stack for our large eCommerce application.

Moreover, the nature of ReactJS allows applications to use dynamic data without reloading the entire page. It’s fast, simple, declarative, scalable, and has gained huge popularity in the eCommerce industry.

Here, the theory of SSR is very simple. All you have to do is send the client the resulting HTML after rendering your React components on the backend. However, implementing it is not as easy as you think.

Let’s understand how we overcome challenges or issues in the code base that are impacted by SSR.

### Transpiling Backend Code

Considering the transpiling, we knew there were two major compilers – Webpack and Babel. In fact, we chose Babel due to its more superficial nature.

We executed babel with the following code for our production build.

`babel . --out-dir ../dist/ --source-maps --copy-files
`



To speed up development when working locally in development mode, we want the server to immediately restart whenever we make code changes. We accomplish this by starting a file called _server.babel.js_ instead of our standard _server.js_. This is how the file appears:

`require("babel-core/register")
require("./server.js")
`



Babel-core/register requires an automatic on-the-fly compilation of the necessary files. We then begin the file with nodemon as follows:

`nodemon server.babel.js
`



We used Nodemon because it restarts the server automatically after the code modification.

### Templating on Backend

Here we came up with a one-liner code to generate the HTML out of React components on the server.

`const app = ReactDomServer.renderToString(component)
`



This generated HTML is placed inside an HTML template that contains definitions for HTML, body tags, etc. We accomplish this by utilizing the handlebars template engine.

Here’s our code snippet using React:

`<!DOCTYPE html>
<html>
<head>
</head>
<body>
<script>
window.__INITIAL_STATE = JSON.parse('{{{JSON.stringify(initialState)}}}');
</script>
<div id="app"></div>
<script>
const initialData = window.__INITIAL_STATE;
const appContainer = document.getElementById('app');

// Render your React app here using the initialData
</script>
</body>
</html>
`



The dynamically generated HTML is seamlessly injected into the designated `{{{app}}}` placeholder. Here, we executed the mounting of React components on the frontend.

Also, we used the template from Express:

`return res.render("appTemplate",
{
app,
initialState,
})
`



### Fetching Data on Initial Loading eCommerce Application

The eCommerce application was a web store that displayed product details for our clients. The product information is stored in backend systems, which we access through REST API. Naturally, we wanted the data to load quickly when the page loads.

In our components, instead of using Ajax, we used Redux and took advantage of its feature. Hence, the initial state was fetched from our backend API and had information about products, cart data, subscriptions, user details, etc.

Our Redux store is created using the following backend `initialState`:

`import { createStore } from 'redux';
import { Provider } from 'react-redux';
import ReactDOMServer from 'react-dom/server';
import reducers from './reducers'; // Import your reducers
import Component from './Component'; // Import your React component

const initialState = {
// Populate with your initial state data (e.g., product info, config)
};

// The initialState is provided to createStore:
const store = createStore(reducers, initialState);

const componentWithStore = (
<Provider store={store}>
<Component />
</Provider>
);

const html = ReactDOMServer.renderToString(componentWithStore);
`



The above code initializes a Redux store with an initial state, wraps your React component with a Redux provider, and then uses `ReactDOMServer.renderToString` to generate HTML on the server side.

In order for the client-side app to receive the exact same state prefetched, the `initialState` variable is also provided to the frontend in a global variable. It appears as follows:

`import { createStore } from 'redux';
import { Provider } from 'react-redux';
import ReactDOM from 'react-dom';
import reducer from './reducer'; // Import your reducer
import Component from './Component'; // Import your React component

const initialState = window.__INITIAL_STATE; // Utilize the same initial state from server side rendering

const store = createStore(reducer, initialState);

ReactDOM.render(
<Provider store={store}>
<Component />
</Provider>,
element // Replace 'element' with the actual DOM element where you want to render the component
);
`



This method of retrieving data during page load for both the client and server-side HTML rendering is the quickest and simplest to maintain, we have found.

> #### Do You Want to Build a Full-stack React SPA with Server-Side Rendering? Hire Experts Today
>
> Let’s Build Isomorphic React App

## Code Splitting

So, here comes the most interesting part – the implementation of SSR.

Yes, we divided our bundle. One bundle included the production code, and the other had the dependencies. That had no effect on how difficult SSR was.

### Not to Give Referencing window and document on the Server

During server-side rendering, you must know that your front end code (React code in this case) is compatible with Node.js. Despite similarities, Node.js and browsers exhibit differences.

Notably, Node.js lacks global variables like `window` and `document`. If your frontend code relies on these variables, it could trigger runtime errors on the backend, akin to the following example:

`ReferenceError: window is not defined
`



The simplest solution is to use an _if_ to prevent running those lines of code on the backend. We may safely omit running those lines because they never change how the React components are rendered in the first place.

In a util library, we defined the functions `isRunningOnClientside` and `isRunningOnServerside`. They are used like this:

`function isRunningOnServerSide() {
return typeof window === "undefined";
}

function isRunningOnClientSide() {
return typeof window !== "undefined";
}
`



When we need to reference anything that should only be referenced by the client, for instance, we guard it with an if.

`function sendToGa(data) {
if (!util.isRunningOnServerSide()) {
window.dataLayer.push(data);
}
}
`



Keep in mind that we used the guard clause pattern, which emphasizes the code's primary flow and eliminates the error flow early. The necessity for nested _ifs_ is also lessened.

The following are some instances of variables that we prevent on the server side:

  * `window.location.search`
  * `window.history.replaceState`
  * `this.isTouchEnabled = 'ontouchstart' in document.documentElement;`
  * Google Analytics (`window.dataLayer, window.google_tag_manager`)
  * Facebook Analytics (`window.fbq`)

## Why Didn’t We Choose Next.js?

When we started working on the eCommerce app development, Next.js didn’t exist in the market. However, after a year – in 2016, it got released. We were very late by then as our code base was large already.

Considering the option of rewriting the entire codebase to use Next.js was a huge task, and we were also running out of time. Hence, we thought to implement Next.js in another eCommerce project we signed up for.

So, our next tech story will be migrating or redeveloping a large eCommerce application with Next.js.

Moreover, as per our ReactJS developers from Radixweb, if Next.js had existed at the project's initial, we don’t think we would have utilized Next.js for the application. Since the technology was new at that time, there are several parameters we always consider, like:

  * The technology should have an active development community in the future and still be relevant.
  * We don’t want ourselves to be restricted from using other tech stacks or infrastructure. We could change any library, framework, or platform per market demands or client needs, right?

We believe that Next.js will maintain its relevance even five years from now. However, our concern is about the difficulty of transitioning away from Next.js if the need arises in the future. **As an opinionated framework, Next.js imposes specific coding practices, which could result in a lock-in effect that we want to avoid for this application.**

## Satisfied Results, But Not an Easy Journey

The results we achieved from our client’s website are commendable. But the journey has not been easy. It required a lot of effort, understanding, and technical expertise in React eight years back. This path has been paved with numerous trials and errors, leading us to significant learning experiences.

_We believe that keeping coding and SSR simplistic is the key to our success with the eCommerce app._ Our approach to simplification and expertise in ReactJS technology has proven to be our greatest ally. We didn’t go for client-side routing or dynamic loading of code. Instead, we followed a simplistic approach – loading data initially.

We could have used all that because of the hype and buzz of technologies. But somewhere, we have been careful not to make things more complicated than they had to be.

So, if you plan to implement ReactJS technology for front end development or SSR in your application, you may consider our expertise. Connect with our ReactJS experts and share your requirements.

Embrace the Future of Speed, Scalability, and Efficiency with NodeJS

Explore Node.js with Us

We're offline

Leave a message

 __