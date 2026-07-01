import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./assets/styles/tokens.css";
import "./assets/styles/global.css";
import { i18n } from "./i18n";

const app = createApp(App);
app.use(createPinia());
app.use(i18n);
app.mount("#app");
