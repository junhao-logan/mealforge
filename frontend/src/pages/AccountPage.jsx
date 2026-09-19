// src/pages/AccountPage.jsx —— 账户页: 用户信息 + 设置(语言)
import { useClerk, useUser } from '@clerk/clerk-react'
import { Globe, LogOut, User as UserIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card } from '@/components/ui/card'
import { setLanguage } from '@/i18n'

export function AccountPage() {
    const { t, i18n } = useTranslation()
    const { user } = useUser()
    const { signOut } = useClerk()
    const lang = (i18n.language || 'en').startsWith('zh') ? 'zh' : 'en'

    const name = user?.fullName || user?.username || '—'
    const email = user?.primaryEmailAddress?.emailAddress || ''

    return (
        <div className="mx-auto max-w-2xl">
            <h1 className="mb-6 text-2xl font-bold text-slate-900">{t('account.title')}</h1>

            {/* 用户信息 */}
            <Card className="mb-4 flex items-center gap-4 p-5">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
                    <UserIcon className="h-6 w-6 text-slate-500" />
                </div>
                <div className="min-w-0">
                    <div className="truncate font-semibold text-slate-900">{name}</div>
                    {email && <div className="truncate text-sm text-slate-500">{email}</div>}
                </div>
            </Card>

            {/* 设置 */}
            <Card className="p-5">
                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
                    {t('account.settings')}
                </h2>

                {/* 语言 */}
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                        <Globe className="h-4 w-4 text-slate-400" />
                        {t('account.language')}
                    </div>
                    <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
                        <LangBtn active={lang === 'en'} onClick={() => setLanguage('en')}>
                            {t('account.english')}
                        </LangBtn>
                        <LangBtn active={lang === 'zh'} onClick={() => setLanguage('zh')}>
                            {t('account.chinese')}
                        </LangBtn>
                    </div>
                </div>
                <p className="mt-2 text-xs text-slate-400">{t('account.languageHint')}</p>
            </Card>

            {/* 退出 */}
            <button
                className="mt-6 flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-red-600"
                onClick={() => signOut()}
            >
                <LogOut className="h-4 w-4" />
                {t('account.signOut')}
            </button>
        </div>
    )
}

function LangBtn({ active, onClick, children }) {
    return (
        <button
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${active
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
                }`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}
