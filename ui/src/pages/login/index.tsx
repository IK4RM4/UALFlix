import { Box, Button, TextField } from "@mui/material";
import { useContext, useState } from "react";
import { AuthContext } from "../../context/auth";

const LoginPage = () => {
  const { setAuthenticated } = useContext(AuthContext);
  const [payload, setPayload] = useState({
    username: "",
    password: "",
  });

  const handleLogin = () => {
    if (payload.username === "admin" && payload.password === "admin") {
      setAuthenticated(true);
    }
  };

  return (
    <Box
      p={1}
      display="flex"
      flexDirection="column"
      gap={1}
      onKeyDown={(e) => {
        if (e.key === "Enter") handleLogin();
      }}
    >
      <TextField
        label="Username"
        value={payload.username}
        onChange={(e) => setPayload({ ...payload, username: e.target.value })}
      />
      <TextField
        label="Password"
        value={payload.password}
        type="password"
        onChange={(e) => setPayload({ ...payload, password: e.target.value })}
      />
      <Button variant="contained" onClick={handleLogin}>
        Login
      </Button>
    </Box>
  );
};

export default LoginPage;
