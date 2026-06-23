import { StudioForm } from "@/components/studio/studio-form";

export default function StudioPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Studio</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Upload one product photo, describe a scene, and generate
          studio-quality lifestyle shots, angles, and seasonal variants — each
          stored per-SKU on Backblaze B2 with SHA-256 provenance.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <StudioForm />
      </div>
    </div>
  );
}
