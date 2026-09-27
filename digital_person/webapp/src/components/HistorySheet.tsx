import { ChatCircleDots, Microphone } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import type { Msg } from '@/hooks/useGuide'
import { MetaRow } from './MetaPills'

// 对话记录抽屉：完整「问—答」历史（按需点开）。主屏只留字幕作答，这里是可回看的存档。
// 跳过 thinking 占位（进行中的回答看主屏字幕，不在历史里显「正在讲解」）。
export default function HistorySheet({ open, onOpenChange, messages }: {
  open: boolean; onOpenChange: (o: boolean) => void; messages: Msg[]
}) {
  const shown = messages.filter((m) => !m.thinking)
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[88vh] max-w-[480px]">
        <DrawerHeader className="pb-1">
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ChatCircleDots className="size-[18px]" weight="duotone" />
            </span>
            对话记录
          </DrawerTitle>
        </DrawerHeader>
        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-1">
          {shown.length === 0 ? (
            <div className="rounded-2xl border bg-card p-4 text-[14px] leading-relaxed text-muted-foreground">
              还没有对话，向导游问点什么吧。
            </div>
          ) : (
            <div className="flex flex-col gap-3 pb-2">
              {shown.map((m) =>
                m.role === 'user' ? (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[82%] rounded-2xl rounded-br-md bg-primary px-3.5 py-2.5 text-[15px] leading-relaxed text-primary-foreground shadow-sm shadow-primary/20">
                      {/* 拍的照片本体：让「我发过什么」在记录里也看得见，而不只是一句「拍了一张照片」 */}
                      {m.image && (
                        <img
                          src={m.image}
                          alt="你发送的照片"
                          className="mb-1.5 max-h-52 w-full rounded-xl border border-primary-foreground/20 object-cover"
                        />
                      )}
                      <p className="whitespace-pre-wrap break-words">
                        {/* 语音来源标记：这条是转写结果，出错时用户一眼知道该怪识别而不是导游 */}
                        {m.voice && <Microphone className="mb-0.5 mr-1 inline size-3.5" weight="duotone" />}
                        {m.text}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div key={m.id} className="flex justify-start">
                    <div className="max-w-[86%] rounded-2xl rounded-bl-md border bg-card px-3.5 py-2.5 text-[15px] leading-relaxed text-card-foreground shadow-sm">
                      <p className="whitespace-pre-wrap break-words">{m.text}</p>
                      {m.meta && <MetaRow meta={m.meta} className="mt-2" />}
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
