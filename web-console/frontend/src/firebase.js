
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

// Fallback to import.meta.env for local development with Vite dev server
const runtimeConfig = window.FIREBASE_CONFIG || {};

const firebaseConfig = {
    apiKey: runtimeConfig.apiKey || import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: runtimeConfig.authDomain || import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: runtimeConfig.projectId || import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: runtimeConfig.storageBucket || import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: runtimeConfig.messagingSenderId || import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: runtimeConfig.appId || import.meta.env.VITE_FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
