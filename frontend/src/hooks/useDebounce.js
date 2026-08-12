// src/hooks/useDebounce.js
// 防抖: 值停止变化 delay 毫秒后才更新返回值。
// 用于搜索框: 用户连续输入时不每个字符都请求, 停顿后才触发一次。复用。
import { useEffect, useState } from 'react'

export function useDebounce(value, delay = 300) {
    const [debounced, setDebounced] = useState(value)
    useEffect(() => {
        const t = setTimeout(() => setDebounced(value), delay)
        return () => clearTimeout(t)   // 值变了就取消上一个定时器
    }, [value, delay])
    return debounced
}