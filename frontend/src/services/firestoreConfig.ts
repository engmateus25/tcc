import { initializeApp } from "firebase/app";
import { getFirestore, type Firestore } from "firebase/firestore";
import { requiredEnv } from "./env";

type FirebaseClientConfig = {
  apiKey: string;
  authDomain: string;
  databaseURL: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  measurementId: string;
};

export let firebaseConfigError: string | null = null;

const firebaseConfig = buildFirebaseConfig();
const app = firebaseConfig ? initializeApp(firebaseConfig) : null;
export const db: Firestore | null = app ? getFirestore(app) : null;

function buildFirebaseConfig(): FirebaseClientConfig | null {
  try {
    return {
      apiKey: requiredEnv("VITE_FIREBASE_API_KEY"),
      authDomain: requiredEnv("VITE_FIREBASE_AUTH_DOMAIN"),
      databaseURL: requiredEnv("VITE_FIREBASE_DATABASE_URL"),
      projectId: requiredEnv("VITE_FIREBASE_PROJECT_ID"),
      storageBucket: requiredEnv("VITE_FIREBASE_STORAGE_BUCKET"),
      messagingSenderId: requiredEnv("VITE_FIREBASE_MESSAGING_SENDER_ID"),
      appId: requiredEnv("VITE_FIREBASE_APP_ID"),
      measurementId: requiredEnv("VITE_FIREBASE_MEASUREMENT_ID"),
    };
  } catch (error) {
    firebaseConfigError = error instanceof Error ? error.message : String(error);
    console.error(firebaseConfigError);
    return null;
  }
}
