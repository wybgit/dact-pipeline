"""
Tests for Chinese character support in logging system.
"""
import pytest
import tempfile
import os
from pathlib import Path
from dact.logger import log, console, info_chinese, error_chinese, warning_chinese, debug_chinese, setup_file_logging


class TestChineseCharacterSupport:
    """Test Chinese character support in logging."""
    
    def test_basic_chinese_logging(self, caplog):
        """Test basic Chinese character logging."""
        chinese_message = "测试中文字符: Hello 世界"
        
        with caplog.at_level("INFO"):
            log.info(chinese_message)
        
        # Verify the message was logged
        assert len(caplog.records) == 1
        # Note: The exact comparison might vary due to Rich formatting
        # We check that Chinese characters are present in some form
        logged_message = str(caplog.records[0].getMessage())
        assert "测试" in logged_message or "中文" in logged_message
    
    def test_chinese_logging_functions(self, caplog):
        """Test specialized Chinese logging functions."""
        test_cases = [
            ("info", info_chinese, "信息: 这是一个信息消息"),
            ("error", error_chinese, "错误: 这是一个错误消息"),
            ("warning", warning_chinese, "警告: 这是一个警告消息"),
            ("debug", debug_chinese, "调试: 这是一个调试消息")
        ]
        
        for level, func, message in test_cases:
            with caplog.at_level("DEBUG"):
                caplog.clear()
                func(message)
                
                if caplog.records:
                    logged_message = str(caplog.records[0].getMessage())
                    # Check that Chinese characters are preserved
                    assert any(char in logged_message for char in ["信息", "错误", "警告", "调试"])
    
    def test_mixed_language_logging(self, caplog):
        """Test logging with mixed Chinese and English."""
        mixed_message = "Test 测试 - English and 中文 mixed content"
        
        with caplog.at_level("INFO"):
            log.info(mixed_message)
        
        assert len(caplog.records) == 1
        logged_message = str(caplog.records[0].getMessage())
        # Verify both English and Chinese characters are present
        assert "Test" in logged_message
        assert ("测试" in logged_message or "中文" in logged_message)
    
    def test_chinese_file_logging(self, tmp_path):
        """Test Chinese character support in file logging."""
        log_file = tmp_path / "chinese_test.log"
        
        # Setup file logging
        file_handler = setup_file_logging(str(log_file), "INFO")
        
        try:
            chinese_message = "文件日志测试: File logging test 中文支持"
            log.info(chinese_message)
            
            # Verify file was created and contains Chinese characters
            assert log_file.exists()
            
            # Read file with UTF-8 encoding
            content = log_file.read_text(encoding='utf-8')
            assert "文件日志测试" in content
            assert "中文支持" in content
            
        finally:
            # Clean up handler
            log.removeHandler(file_handler)
            file_handler.close()
    
    def test_console_chinese_output(self):
        """Test console Chinese character output."""
        # This test verifies that console can handle Chinese characters
        # without throwing encoding errors
        chinese_text = "控制台输出测试: Console output test"
        
        try:
            # This should not raise any encoding errors
            console.print(chinese_text)
            console.print(f"[green]{chinese_text}[/green]")
            console.print(f"[red]错误消息[/red]: Error message")
            console.print(f"[yellow]警告消息[/yellow]: Warning message")
            
            # If we reach here, Chinese output is working
            assert True
        except UnicodeEncodeError:
            pytest.fail("Console failed to handle Chinese characters")
    
    def test_chinese_in_rich_markup(self):
        """Test Chinese characters in Rich markup."""
        test_cases = [
            "[green]成功[/green]: 操作完成",
            "[red]失败[/red]: 操作失败", 
            "[yellow]警告[/yellow]: 注意事项",
            "[blue]信息[/blue]: 提示信息"
        ]
        
        for markup_text in test_cases:
            try:
                console.print(markup_text)
                # If no exception is raised, the test passes
                assert True
            except Exception as e:
                pytest.fail(f"Rich markup failed with Chinese characters: {e}")
    
    def test_chinese_parameter_rendering(self, caplog):
        """Test Chinese characters in parameter rendering scenarios."""
        # Simulate parameter rendering with Chinese content
        params = {
            "中文参数": "中文值",
            "english_param": "English value",
            "mixed_param": "Mixed 混合 content"
        }
        
        with caplog.at_level("INFO"):
            for key, value in params.items():
                log.info(f"参数 {key}: {value}")
        
        # Verify all messages were logged
        assert len(caplog.records) == 3
        
        # Check that Chinese characters are preserved in parameter names and values
        all_messages = " ".join([str(record.getMessage()) for record in caplog.records])
        assert "中文参数" in all_messages
        assert "中文值" in all_messages
        assert "混合" in all_messages


class TestLoggingModes:
    """Test different logging modes (simple and debug)."""
    
    def test_simple_mode_chinese(self, caplog):
        """Test simple logging mode with Chinese characters."""
        with caplog.at_level("INFO"):
            log.info("简单模式: 执行命令成功")
        
        assert len(caplog.records) == 1
        message = str(caplog.records[0].getMessage())
        assert "简单模式" in message
    
    def test_debug_mode_chinese(self, caplog):
        """Test debug logging mode with Chinese characters."""
        with caplog.at_level("DEBUG"):
            log.debug("调试模式: 详细执行信息")
            log.debug("参数值: param1=值1, param2=值2")
            log.debug("执行状态: 正在处理中...")
        
        assert len(caplog.records) == 3
        all_messages = " ".join([str(record.getMessage()) for record in caplog.records])
        assert "调试模式" in all_messages
        assert "参数值" in all_messages
        assert "执行状态" in all_messages


class TestErrorHandling:
    """Test error handling with Chinese characters."""
    
    def test_chinese_error_messages(self, caplog):
        """Test error messages with Chinese characters."""
        error_messages = [
            "错误: 文件未找到",
            "异常: 参数验证失败",
            "失败: 命令执行超时"
        ]
        
        with caplog.at_level("ERROR"):
            for msg in error_messages:
                log.error(msg)
        
        assert len(caplog.records) == 3
        all_messages = " ".join([str(record.getMessage()) for record in caplog.records])
        assert "错误" in all_messages
        assert "异常" in all_messages
        assert "失败" in all_messages
    
    def test_chinese_exception_logging(self, caplog):
        """Test exception logging with Chinese characters."""
        try:
            raise ValueError("中文异常消息: Invalid parameter value")
        except ValueError as e:
            with caplog.at_level("ERROR"):
                log.error(f"捕获异常: {str(e)}")
        
        assert len(caplog.records) == 1
        message = str(caplog.records[0].getMessage())
        assert "捕获异常" in message
        assert "中文异常消息" in message