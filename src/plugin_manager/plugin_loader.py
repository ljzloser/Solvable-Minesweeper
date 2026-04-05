"""
插件加载器

支持动态导入插件模块，从指定目录发现和加载插件
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import loguru

if TYPE_CHECKING:
    from .plugin_base import BasePlugin, PluginInfo

logger = loguru.logger.bind(name="PluginLoader")


class PluginLoader:
    """
    插件加载器
    
    功能：
    - 从目录发现插件模块
    - 动态导入插件
    - 实例化插件类
    """
    
    def __init__(self, plugin_dirs: list[str | Path] | None = None):
        self._plugin_dirs: list[Path] = []
        if plugin_dirs:
            for d in plugin_dirs:
                self.add_plugin_dir(d)
    
    def add_plugin_dir(self, path: str | Path) -> None:
        """添加插件搜索目录"""
        p = Path(path)
        if p.is_dir():
            self._plugin_dirs.append(p)
            logger.debug(f"Added plugin directory: {p}")
        else:
            logger.warning(f"Plugin directory not found: {p}")
    
    def discover_plugins(self) -> list[tuple[Path, str]]:
        """发现所有插件模块"""
        plugins = []
        
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.is_dir():
                continue
            
            # 单文件插件
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                plugins.append((py_file, py_file.stem))
                logger.debug(f"Discovered plugin module: {py_file}")
            
            # 包形式插件
            for pkg_dir in plugin_dir.iterdir():
                if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
                    if not pkg_dir.name.startswith("_"):
                        plugins.append((pkg_dir / "__init__.py", pkg_dir.name))
                        logger.debug(f"Discovered plugin package: {pkg_dir}")
        
        return plugins
    
    def load_module(self, module_path: Path, module_name: str) -> object | None:
        """动态加载模块"""
        try:
            if module_name in sys.modules:
                return sys.modules[module_name]
            
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create spec for: {module_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            logger.info(f"Loaded plugin module: {module_name}")
            return module
            
        except Exception as e:
            logger.error(f"Failed to load module {module_path}: {e}", exc_info=True)
            return None
    
    def get_plugin_classes(self, module: object) -> list[type[BasePlugin]]:
        """从模块中提取插件类"""
        from .plugin_base import BasePlugin
        
        plugin_classes: list[type[BasePlugin]] = []
        
        for name in dir(module):
            if name.startswith("_"):
                continue
            
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BasePlugin)
                and obj is not BasePlugin
            ):
                plugin_classes.append(obj)
                logger.debug(f"Found plugin class: {obj.__name__}")
        
        return plugin_classes
    
    def load_plugins_from_module(
        self,
        module_path: Path,
        module_name: str,
    ) -> list[BasePlugin]:
        """从模块加载所有插件实例"""
        plugins: list[BasePlugin] = []
        
        module = self.load_module(module_path, module_name)
        if module is None:
            return plugins
        
        plugin_classes = self.get_plugin_classes(module)
        
        for plugin_class in plugin_classes:
            try:
                info = self._get_plugin_info(plugin_class)
                plugin = plugin_class(info)
                plugins.append(plugin)
                logger.info(f"Instantiated plugin: {plugin.name}")
            except Exception as e:
                logger.error(
                    f"Failed to instantiate plugin {plugin_class.__name__}: {e}",
                    exc_info=True,
                )
        
        return plugins
    
    def _get_plugin_info(self, plugin_class: type[BasePlugin]) -> PluginInfo:
        """获取插件的元信息"""
        return plugin_class.plugin_info()
    
    def load_all(self) -> list[BasePlugin]:
        """加载所有发现的插件"""
        all_plugins: list[BasePlugin] = []
        
        discovered = self.discover_plugins()
        for module_path, module_name in discovered:
            plugins = self.load_plugins_from_module(module_path, module_name)
            all_plugins.extend(plugins)
        
        logger.info(f"Loaded {len(all_plugins)} plugin(s)")
        return all_plugins
    
    def reload_module(self, module_name: str) -> bool:
        """重新加载模块"""
        if module_name not in sys.modules:
            logger.warning(f"Module not loaded: {module_name}")
            return False
        
        try:
            importlib.reload(sys.modules[module_name])
            logger.info(f"Reloaded module: {module_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload module {module_name}: {e}", exc_info=True)
            return False