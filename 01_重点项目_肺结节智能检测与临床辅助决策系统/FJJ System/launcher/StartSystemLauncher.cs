using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

class StartSystemLauncher
{
    static int Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;

        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        string appRoot = Directory.Exists(Path.Combine(root, "system"))
            ? Path.Combine(root, "system")
            : root;
        string python = Path.Combine(root, "runtime", "python", "python.exe");
        string app = Path.Combine(appRoot, "app2.py");

        Console.WriteLine("肺结节智能辅助诊断工作台");
        Console.WriteLine("--------------------------------");

        if (!File.Exists(python))
        {
            Console.WriteLine("未找到内置 Python 运行时：");
            Console.WriteLine(python);
            Console.WriteLine("请确认使用的是完整离线包，不要删除 runtime 文件夹。");
            Console.WriteLine("按任意键退出。");
            Console.ReadKey();
            return 1;
        }

        if (!File.Exists(app))
        {
            Console.WriteLine("未找到系统入口 app2.py，程序包不完整。");
            Console.WriteLine(app);
            Console.WriteLine("按任意键退出。");
            Console.ReadKey();
            return 1;
        }

        string existingPythonPath = Environment.GetEnvironmentVariable("PYTHONPATH") ?? "";
        string vendorPath = Path.Combine(appRoot, "vendor");
        Environment.SetEnvironmentVariable("PYTHONPATH", vendorPath + ";" + appRoot + ";" + existingPythonPath);

        if (String.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("LLM_API_BASE")))
        {
            Environment.SetEnvironmentVariable("LLM_API_BASE", "https://ai.rjyunk.com/v1");
        }
        if (String.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("LLM_MODEL")))
        {
            Environment.SetEnvironmentVariable("LLM_MODEL", "gpt-5.3-codex-spark");
        }

        Console.WriteLine("正在启动本地服务，请稍等...");
        Console.WriteLine("访问地址：http://127.0.0.1:5001");
        Console.WriteLine("关闭本窗口会停止服务。");
        Console.WriteLine();

        var startInfo = new ProcessStartInfo();
        startInfo.FileName = python;
        startInfo.Arguments = "app2.py";
        startInfo.WorkingDirectory = appRoot;
        startInfo.UseShellExecute = false;

        Process server;
        try
        {
            server = Process.Start(startInfo);
        }
        catch (Exception ex)
        {
            Console.WriteLine("启动失败：" + ex.Message);
            Console.WriteLine("按任意键退出。");
            Console.ReadKey();
            return 1;
        }

        Thread.Sleep(3500);
        try
        {
            Process.Start(new ProcessStartInfo("http://127.0.0.1:5001") { UseShellExecute = true });
        }
        catch
        {
            Console.WriteLine("浏览器未能自动打开，请手动访问 http://127.0.0.1:5001");
        }

        server.WaitForExit();
        return server.ExitCode;
    }
}
