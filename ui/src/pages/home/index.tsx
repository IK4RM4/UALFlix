import { Box, Button } from "@mui/material";
import { useEffect, useState } from "react";
import useApi from "../../api";

const HomePage = () => {
  const { getVideos } = useApi();
  const [videos, setVideos] = useState<any[]>([]);

  const fetchVideos = async () => {
    const videos = await getVideos();
    setVideos(videos);
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  return (
    <Box>
      <Button variant="contained" onClick={fetchVideos}>
        Atualizar Vídeos
      </Button>
      <Box p={1} display="flex" flexDirection="column" gap={1}>
        {videos.length > 0
          ? videos.map((video) => (
              <Box key={JSON.stringify(video)}>{JSON.stringify(video)}</Box>
            ))
          : "Nenhum vídeo encontrado."}
      </Box>
    </Box>
  );
};

export default HomePage;
