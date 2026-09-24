// src/components/mealplan/RestockChoiceDialog.jsx
// A5: 删除已完成的餐次 / 含已完成餐次的计划时, 问用户要不要把扣掉的库存退回去。
// 三个按钮: 取消 / 只删记录(饭确实吃了) / 删除并退回库存(其实没做)。
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'

export function RestockChoiceDialog({ open, title, message, busy, onChoose, onCancel }) {
    const { t } = useTranslation()
    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o && !busy) onCancel?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                </DialogHeader>
                <p className="text-sm text-slate-600">{message}</p>
                <div className="flex flex-wrap justify-end gap-2 pt-2">
                    <button
                        className="rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50"
                        disabled={busy}
                        onClick={onCancel}
                    >
                        {t('common.cancel')}
                    </button>
                    <button
                        className="rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                        disabled={busy}
                        onClick={() => onChoose(false)}
                    >
                        {t('meal.deleteRecordOnly')}
                    </button>
                    <button
                        className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                        disabled={busy}
                        onClick={() => onChoose(true)}
                    >
                        {t('meal.deleteAndRestock')}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
