// src/i18n/index.js —— react-i18next 初始化。默认英文, 记住上次选择。
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './en.json'
import zh from './zh.json'

const LANG_KEY = 'mf_lang'

function savedLang() {
    try {
        return localStorage.getItem(LANG_KEY)
    } catch {
        return null
    }
}

i18n.use(initReactI18next).init({
    resources: {
        en: { translation: en },
        zh: { translation: zh },
    },
    lng: savedLang() || 'en',   // 默认英文
    fallbackLng: 'en',
    interpolation: { escapeValue: false },   // React 已转义
})

// 切换语言并持久化。组件调用 setLanguage('zh') 即可。
export function setLanguage(lng) {
    i18n.changeLanguage(lng)
    try {
        localStorage.setItem(LANG_KEY, lng)
    } catch {
        // localStorage 不可用时忽略(隐私模式等)
    }
}

export default i18n
