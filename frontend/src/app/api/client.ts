import axios from "axios";

/**
 * Axios instance configured with the backend base URL. The environment
 * variable NEXT_PUBLIC_BACKEND_URL can be set to point to the FastAPI
 * service (defaults to http://localhost:8000). All API calls from the
 * frontend should use this instance.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
});