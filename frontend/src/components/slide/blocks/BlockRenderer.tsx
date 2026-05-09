import React from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import type { CanvasBlock } from '@/store/slideEditorStore'

interface Props {
  block: CanvasBlock
  onUpdate: (id: number, updates: Partial<CanvasBlock>) => void
}

function TipTapBlock({ block, onUpdate }: Props) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: (block.content as { html?: string }).html || '',
    onUpdate: ({ editor }) => {
      onUpdate(block.id, { content: { html: editor.getHTML() } })
    },
  })
  return <EditorContent editor={editor} className="h-full overflow-auto p-2 text-sm" />
}

export function BlockRenderer({ block, onUpdate }: Props) {
  switch (block.type) {
    case 'text':
    case 'heading':
      return <TipTapBlock block={block} onUpdate={onUpdate} />
    case 'image':
      return (
        <div className="p-2 h-full flex flex-col gap-1">
          <input
            className="text-xs border rounded px-1 py-0.5 w-full"
            placeholder="Image URL"
            defaultValue={(block.content as { url?: string }).url || ''}
            onBlur={(e) => onUpdate(block.id, { content: { ...block.content, url: e.target.value } })}
          />
          {(block.content as { url?: string }).url && (
            <img
              src={(block.content as { url: string }).url}
              alt="block"
              className="flex-1 object-contain"
            />
          )}
        </div>
      )
    case 'code':
      return (
        <textarea
          className="w-full h-full p-2 text-xs font-mono resize-none border-0 bg-gray-900 text-green-400"
          placeholder="// code here"
          defaultValue={(block.content as { code?: string }).code || ''}
          onBlur={(e) => onUpdate(block.id, { content: { ...block.content, code: e.target.value } })}
        />
      )
    case 'divider':
      return <hr className="w-full border-gray-300 my-auto" />
    default:
      return (
        <textarea
          className="w-full h-full p-2 text-sm resize-none border-0"
          placeholder={`${block.type} content`}
          defaultValue={(block.content as { text?: string }).text || ''}
          onBlur={(e) => onUpdate(block.id, { content: { ...block.content, text: e.target.value } })}
        />
      )
  }
}
