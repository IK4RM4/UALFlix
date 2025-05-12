import { useContext } from "react";
import { AuthContext } from "./context/auth";
import HomePage from "./pages/home";
import LoginPage from "./pages/login";

function App() {
  const { authenticated } = useContext(AuthContext);

  return <>{authenticated ? <HomePage /> : <LoginPage />}</>;
}

export default App;
