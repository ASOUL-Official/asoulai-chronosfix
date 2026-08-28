param(
  [Parameter(Mandatory = $true)][string]$InputPptx,
  [Parameter(Mandatory = $true)][string]$OutputPdf
)

$ppt = $null
$presentation = $null
try {
  $ppt = New-Object -ComObject PowerPoint.Application
  $presentation = $ppt.Presentations.Open($InputPptx, $true, $false, $false)
  # 32 = ppSaveAsPDF; PowerPoint keeps text/shapes as vector objects.
  $presentation.SaveAs($OutputPdf, 32)
  Write-Output $OutputPdf
}
finally {
  if ($presentation) { $presentation.Close() }
  if ($ppt) { $ppt.Quit() }
  foreach ($com in @($presentation, $ppt)) {
    if ($com) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($com) }
  }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
