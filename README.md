# PyStandMate

这里假设你已经知道 [PyStand](https://github.com/skywind3000/PyStand) 是做什么用的。PyStandMate 可以看作是一个 PyStand 打包助手。它提供了一个命令行工具，以自动化 PyStand 打包流程。具体工作流程如下：

1. 从 PyStand 的 [Release](https://github.com/skywind3000/PyStand/releases) 页面自动下载指定版本的 `PyStand.exe`；
2. 从 Python 官网下载指定版本的 [Windows embeddable Python](https://www.python.org/downloads/windows/) 压缩包；
3. 自动安装 pip 及指定的第三方包；
4. 将上述三步下载的文件按照 PyStand 要求的目录结构进行组织；
5. 利用 GitHub Actions 自动执行如上流程，并将打包好的文件上传；

命令行参数：

- --pystand-version：指定 PyStand 的 Release 版本，仅支持 PyStand 1.0.11 及以上版本，默认值为 1.0.11；
- --bitness：指定 PyStand 的位数，必须是 32 或 64；默认值为 32；
- --compiler：指定用于生成 PyStand 的编译器，必须是 MSVC 或 GCC；默认值为 MSVC；
- --console：当指定该参数时，表示使用 PyStand 的命令行版本；默认使用 PyStand GUI 版本；
- --pystand-int：PyStand 启动脚本 `PyStand.int` 文件路径；
- --python-version：指定 Python 版本；当指定一个不可用的 Python 版本时，程序将自动从 Python 下载页面获取所有可用的 Python 版本列表，并打印出来；默认值为 3.8.10；
- --package：指定需要额外下载的第三方包；也可以指定一个 `requirements.txt`；
- --pip-index-url：指定 PyPI 镜像 base URL（如：https://mirrors.tuna.tsinghua.edu.cn/help/pypi/ 、https://pypi.doubanio.com/simple ）；默认值为 https://pypi.python.org/simple ；
- --response-file：用户可以将要传递给 PyStandMate.py 的命令行参数存储在文本文件（我们称之为“Response file”）中，然后通过该参数指定 Response file；`PyStandMate.rsp` 便是一个存储了命令行参数的 Response file；

用户可以通过：

```
python .\PyStandMate.py --help
```

获取完整的命令行帮助。

# 如何使用？

### 方式一：在本地计算机上运行

1. 将本仓库的代码克隆或下载到本地；

2. 按照自己的需求修改 `PyStandMate.rsp`；

3. 将要下载的第三方包逐行写入 `requirements.txt`；

4. 通过命令行运行：

   ```
   python .\PyStandMate.py --response-file PyStandMate.rsp
   ```

### 方式二：通过 GitHub Actions 实现自动化

1. Fork 本仓库；
2. 按照自己的需求修改 `PyStandMate.rsp`；
3. 将要下载的第三方包逐行写入 `requirements.txt`；
4. 提交上述两步的更改，触发 GitHub Actions CI；待 CI 跑完后，即可从相应 Workflow run 的 Summary 页面下载生成的 Artifacts；
5. 如果需要将上一步的 Artifacts 发布在 GitHub Release 页面，可以在最新的提交上添加一个 Tag，并将该 Tag 推送至 GitHub；

# TODO

* [x] ~~移除 `.dist-info` 文件夹；~~
* [x] ~~自动打包 `PyStand.int` 文件；~~
* [ ] 增加一些 glob 规则文件，以实现包的自动裁剪；

# License

MIT