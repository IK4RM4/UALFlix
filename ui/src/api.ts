const useApi = () => {
  const getVideos = async () => {
    const response = await fetch(`http://localhost:8000/videos`, {
      method: "GET",
    }).catch(console.error);
    return response?.json();
  };

  return { getVideos };
};

export default useApi;
