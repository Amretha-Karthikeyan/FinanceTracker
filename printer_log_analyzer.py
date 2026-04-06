import re
from typing import List, Dict

class PrinterLogAnalyzer:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.entries = self._load_log()

    def _load_log(self) -> List[str]:
        with open(self.log_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def find_errors(self) -> List[Dict]:
        errors = []
        for i, line in enumerate(self.entries):
            if 'error' in line.lower():
                context = self.entries[max(0, i-5):i+1]  # 5 lines before error
                errors.append({
                    'error_line': line.strip(),
                    'context': [l.strip() for l in context],
                    'issue': self._explain_issue(line)
                })
        return errors

    def _explain_issue(self, error_line: str) -> str:
        # Simple explanation based on error keywords
        if 'paper jam' in error_line.lower():
            return 'Paper jam detected. Check printer tray.'
        elif 'out of toner' in error_line.lower():
            return 'Printer is out of toner.'
        elif 'offline' in error_line.lower():
            return 'Printer is offline. Check network or power.'
        else:
            return 'Unknown error. Check log details.'

    def summarize_errors(self):
        errors = self.find_errors()
        for idx, err in enumerate(errors):
            print(f"Error {idx+1}: {err['error_line']}")
            print("Context:")
            for ctx in err['context']:
                print(f"  {ctx}")
            print(f"Issue: {err['issue']}\n")

if __name__ == '__main__':
    log_path = 'c:/Users/natarani/Downloads/printerlog.FW35.Typhoon'
    analyzer = PrinterLogAnalyzer(log_path)
    analyzer.summarize_errors()
