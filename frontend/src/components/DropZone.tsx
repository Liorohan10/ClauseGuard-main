import { useCallback, useState, useRef } from 'react';
import { Upload, FileUp, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DropZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  loading?: boolean;
}

const ACCEPTED = ['.pdf', '.txt'];

export function DropZone({ onFile, disabled, loading }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!ACCEPTED.includes(ext)) {
        alert('Only .pdf and .txt files are accepted.');
        return;
      }
      onFile(file);
    },
    [onFile]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 p-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
        </div>
        <div>
          <p className="font-semibold">Analyzing contract...</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Extracting clauses with AI. This may take a moment.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        'flex cursor-pointer flex-col items-center gap-4 rounded-xl border-2 border-dashed p-16 text-center transition-all',
        dragging
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-muted-foreground/20 hover:border-primary/40 hover:bg-muted/50',
        disabled && 'pointer-events-none opacity-50'
      )}
    >
      <div className={cn(
        'flex h-14 w-14 items-center justify-center rounded-full transition-colors',
        dragging ? 'bg-primary/15' : 'bg-muted'
      )}>
        {dragging ? (
          <FileUp className="h-7 w-7 text-primary" />
        ) : (
          <Upload className="h-7 w-7 text-muted-foreground" />
        )}
      </div>
      <div>
        <p className="font-semibold">
          {dragging ? 'Drop your file here' : 'Drag & drop a contract file'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          or click to browse. Supports PDF and TXT files.
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = '';
        }}
      />
    </div>
  );
}
