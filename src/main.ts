import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'

// 明色主题（B 阅读器方案）：走 Element Plus 默认 light 变量，
// 主色在 style.css 的 :root 里重排成 B站粉。这里不再挂 html.dark。
createApp(App).use(ElementPlus, { locale: zhCn }).mount('#app')
