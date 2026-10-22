import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './style.css'
import App from './App.vue'

// 整站固定暗色：Element Plus 的 dark 变量挂在 html.dark 上
document.documentElement.classList.add('dark')

createApp(App).use(ElementPlus, { locale: zhCn }).mount('#app')
