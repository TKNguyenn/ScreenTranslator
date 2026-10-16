using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

internal static class Uninstall
{
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            foreach (string arg in args)
                if (!Array.Exists(new[] { "/VERYSILENT", "/SILENT", "/SUPPRESSMSGBOXES",
                    "/NORESTART", "/DATA=keep", "/DATA=all" },
                    value => String.Equals(value, arg, StringComparison.OrdinalIgnoreCase)))
                    throw new InvalidOperationException("Unsupported uninstall argument.");

            using (RegistryKey user = RegistryKey.OpenBaseKey(RegistryHive.CurrentUser, RegistryView.Registry64))
            using (RegistryKey key = user.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\AIScreenTranslator-96F65CB7-531C-4202-B340-B90251E5B2AC_is1"))
            {
                if (key == null)
                    throw new InvalidOperationException("AI Screen Translator is not installed for this Windows user.");
                Version version;
                if (!Version.TryParse(key.GetValue("DisplayVersion", "").ToString(), out version) ||
                    version < new Version(0, 4, 1, 7))
                    throw new InvalidOperationException("Install AI Screen Translator 0.4.1.7 or newer first to enable the two uninstall options.");
                string folder = key.GetValue("InstallLocation", "").ToString();
                if (!Path.IsPathRooted(folder) || !File.Exists(Path.Combine(folder, "unins000.exe")))
                    throw new InvalidOperationException("The installed uninstaller is missing. Reinstall the app, then try again.");
                // Exit immediately so the native uninstaller can remove this launcher too.
                Process.Start(new ProcessStartInfo(Path.Combine(folder, "unins000.exe"), String.Join(" ", args))
                    { UseShellExecute = true });
            }
            return 0;
        }
        catch (Exception error)
        {
            if (args.Length == 0)
                MessageBox.Show(error.Message, "AI Screen Translator - Uninstall", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return 1;
        }
    }
}
