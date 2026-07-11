// MVP 骨架：登录 UI 直接内联在 App。正式前端（Week 10）会拆为
// pages/SignInPage + components/Header + lib/api 的分层结构。
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react'

function App() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>MealForge</h1>

      <SignedOut>
        <p>你还没登录。</p>
        <SignInButton />
      </SignedOut>

      <SignedIn>
        <p>已登录 ✅</p>
        <UserButton />
      </SignedIn>
    </div>
  )
}

export default App