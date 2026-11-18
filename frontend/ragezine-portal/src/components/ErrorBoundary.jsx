import { Component } from "react";

import ErrorPage from "../pages/ErrorPage";

export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <ErrorPage status={500} />;
    }
    return this.props.children;
  }
}
