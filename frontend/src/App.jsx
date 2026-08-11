// src/App.jsx —— 路由表 + 登录保护
import { SignedIn, SignedOut, SignInButton } from '@clerk/clerk-react'
import { Route, Routes } from 'react-router'

import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { InventoryPage } from '@/pages/InventoryPage'
import { MealPlansPage } from '@/pages/MealPlansPage'
import { NutritionPage } from '@/pages/NutritionPage'
import { RecipesPage } from '@/pages/RecipesPage'
import { ShoppingPage } from '@/pages/ShoppingPage'

// 未登录时的落地页
function LandingPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="rounded-xl bg-white p-10 text-center shadow-lg">
        <h1 className="text-3xl font-bold text-slate-900">MealForge</h1>
        <p className="mt-2 text-slate-500">AI 膳食管理</p>
        <div className="mt-6">
          <SignInButton mode="modal">
            <button className="rounded-lg bg-slate-900 px-6 py-2 font-medium text-white hover:bg-slate-800">
              登录
            </button>
          </SignInButton>
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <>
      {/* 登录了才显示应用; 没登录显示落地页 */}
      <SignedIn>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="inventory" element={<InventoryPage />} />
            <Route path="recipes" element={<RecipesPage />} />
            <Route path="meal-plans" element={<MealPlansPage />} />
            <Route path="shopping" element={<ShoppingPage />} />
            <Route path="nutrition" element={<NutritionPage />} />
          </Route>
        </Routes>
      </SignedIn>
      <SignedOut>
        <LandingPage />
      </SignedOut>
    </>
  )
}

export default App