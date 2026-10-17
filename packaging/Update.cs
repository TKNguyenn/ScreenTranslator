using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Windows.Forms;

internal static class Update
{
    [STAThread]
    private static int Main(string[] args)
    {
        string log = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "update.log");
        try
        {
            int pid;
            if (args.Length != 4 || !Path.IsPathRooted(args[0]) || !Path.IsPathRooted(args[2]) ||
                !Int32.TryParse(args[3], out pid) || pid <= 0 || args[1].Length != 64)
                throw new InvalidOperationException("Invalid update arguments.");
            string installer = Path.GetFullPath(args[0]);
            string folder = Path.GetFullPath(args[2]);
            if (!File.Exists(installer) || !File.Exists(Path.Combine(folder, "ScreenTranslator.exe")))
                throw new FileNotFoundException("Installer or installed application is missing.");
            Process parent = null;
            try { parent = Process.GetProcessById(pid); }
            catch (ArgumentException) { } // The app may already have finished shutting down.
            if (parent != null)
                using (parent)
                    if (!parent.WaitForExit(60000))
                        throw new InvalidOperationException("The app is still running. Exit it, then try the update again.");
            // Keep a read lock until Setup exits so the verified installer cannot change during handoff.
            using (FileStream stream = File.OpenRead(installer))
            {
                using (SHA256 hash = SHA256.Create())
                    if (!String.Equals(BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", ""),
                                       args[1], StringComparison.OrdinalIgnoreCase))
                        throw new InvalidOperationException("Installer SHA256 does not match. No update was installed.");
                using (Process setup = Process.Start(new ProcessStartInfo(installer,
                    "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /UPDATE=1 /DIR=\"" + folder + "\" /LOG=\"" + log + "\"")
                    { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(installer) }))
                {
                    setup.WaitForExit();
                    if (setup.ExitCode != 0)
                        throw new InvalidOperationException("Setup did not complete (code " + setup.ExitCode + "). See " + log);
                }
            }
            Process.Start(new ProcessStartInfo(Path.Combine(folder, "ScreenTranslator.exe"))
                { UseShellExecute = true, WorkingDirectory = folder });
            try { File.Delete(installer); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            return 0;
        }
        catch (Exception error)
        {
            try { File.AppendAllText(log, Environment.NewLine + error.Message); } catch (Exception) { }
            MessageBox.Show(error.Message + Environment.NewLine + "You can reopen the app from its shortcut.",
                "AI Screen Translator - Update", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
