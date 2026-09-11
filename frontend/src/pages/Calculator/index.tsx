/**
 * Calculator — stealth screen that disguises the accounting app.
 * It is a fully functional calculator.
 * When the user types the secret unlock code and presses =,
 * the app transitions to the login screen.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { setUnlocked } from '../../store/auth';
import { api } from '../../api/client';

// Secret code — fetched once from server; fallback to env var
let SECRET_CODE = import.meta.env.VITE_UNLOCK_CODE || '2809';

(async () => {
  try {
    const res = await api.get('/settings/unlock-code');
    SECRET_CODE = res.data.code;
  } catch {}
})();

const BTN = [
  ['AC', '+/-', '%', '÷'],
  ['7',  '8',   '9', '×'],
  ['4',  '5',   '6', '−'],
  ['1',  '2',   '3', '+'],
  ['0',  '',   '.', '='],
];

export default function Calculator() {
  const navigate = useNavigate();
  const [display, setDisplay] = useState('0');
  const [prev, setPrev] = useState<number | null>(null);
  const [op, setOp] = useState<string | null>(null);
  const [fresh, setFresh] = useState(true);
  const [secretBuffer, setSecretBuffer] = useState('');
  const [unlocking, setUnlocking] = useState(false);

  const calculate = useCallback((a: number, b: number, operator: string): number => {
    switch (operator) {
      case '+': return a + b;
      case '−': return a - b;
      case '×': return a * b;
      case '÷': return b !== 0 ? a / b : 0;
      default: return b;
    }
  }, []);

  const press = useCallback((key: string) => {
    if (key === '') return;

    if (key === 'AC') {
      setDisplay('0');
      setPrev(null);
      setOp(null);
      setFresh(true);
      setSecretBuffer('');
      return;
    }

    if (key === '+/-') {
      setDisplay(d => d.startsWith('-') ? d.slice(1) : '-' + d);
      return;
    }

    if (key === '%') {
      setDisplay(d => String(parseFloat(d) / 100));
      return;
    }

    if (['÷', '×', '−', '+'].includes(key)) {
      setPrev(parseFloat(display));
      setOp(key);
      setFresh(true);
      return;
    }

    if (key === '=') {
      // Check secret code BEFORE computing
      const fullInput = secretBuffer + display;
      if (fullInput === SECRET_CODE || display === SECRET_CODE || secretBuffer.replace(/[^0-9]/g, '') + display === SECRET_CODE) {
        // Unlock!
        setUnlocking(true);
        setTimeout(() => {
          setUnlocked();
          navigate('/login');
        }, 400);
        return;
      }

      if (prev !== null && op !== null) {
        const result = calculate(prev, parseFloat(display), op);
        const resultStr = Number.isInteger(result) ? String(result) : result.toFixed(6).replace(/\.?0+$/, '');
        setDisplay(resultStr);
        setPrev(null);
        setOp(null);
        setFresh(true);
        setSecretBuffer('');
      }
      return;
    }

    if (key === '.') {
      if (fresh) { setDisplay('0.'); setFresh(false); return; }
      if (!display.includes('.')) setDisplay(d => d + '.');
      return;
    }

    // Number key
    if (fresh) {
      setDisplay(key);
      setFresh(false);
      // Track secret code: accumulate digits including previous operator inputs
      setSecretBuffer(b => b + key);
    } else {
      const next = display === '0' ? key : display + key;
      setDisplay(next);
      setSecretBuffer(b => b + key);
    }
  }, [display, prev, op, fresh, secretBuffer, calculate, navigate]);

  // Physical keyboard support
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const map: Record<string, string> = {
        '0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',
        '.':'.','Enter':'=','=':'=','Escape':'AC',
        '+':'+','-':'−','*':'×','/':'÷','%':'%',
      };
      if (map[e.key]) press(map[e.key]);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [press]);

  const isOrange = (k: string) => ['÷','×','−','+','='].includes(k);
  const isGray = (k: string) => ['AC','+/-','%'].includes(k);

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#000',
      userSelect: 'none',
      opacity: unlocking ? 0 : 1,
      transition: 'opacity 0.4s ease',
    }}>
      {/* Display */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        padding: '0 24px 8px',
      }}>
        {op && (
          <div style={{ fontSize: 22, color: 'rgba(255,255,255,0.4)', textAlign: 'right', marginBottom: 4 }}>
            {prev} {op}
          </div>
        )}
        <div style={{
          fontSize: display.length > 9 ? 48 : display.length > 6 ? 64 : 80,
          fontWeight: '300',
          color: '#fff',
          textAlign: 'right',
          letterSpacing: -2,
          lineHeight: 1,
          transition: 'font-size 0.1s',
          minHeight: 90,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'flex-end',
        }}>
          {display}
        </div>
      </div>

      {/* Keypad */}
      <div style={{ padding: '0 12px 40px' }}>
        {BTN.map((row, ri) => (
          <div key={ri} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            {row.map((key, ki) => {
              if (key === '') return <div key={ki} style={{ flex: 1 }} />;
              const wide = key === '0';
              return (
                <button
                  key={ki}
                  onClick={() => press(key)}
                  style={{
                    flex: wide ? 2 : 1,
                    aspectRatio: wide ? 'unset' : '1',
                    height: 76,
                    borderRadius: wide ? 38 : '50%',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: key === 'AC' || key === '+/-' || key === '%' ? 20 : 28,
                    fontWeight: 400,
                    fontFamily: 'inherit',
                    paddingLeft: wide ? 28 : 0,
                    textAlign: wide ? 'left' : 'center',
                    background: isOrange(key)
                      ? '#ff9f0a'
                      : isGray(key)
                        ? '#a5a5a5'
                        : '#333333',
                    color: isGray(key) ? '#000' : '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: wide ? 'flex-start' : 'center',
                    transition: 'filter 0.1s, transform 0.08s',
                    WebkitTapHighlightColor: 'transparent',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                  onTouchStart={e => {
                    const btn = e.currentTarget;
                    btn.style.filter = 'brightness(1.5)';
                  }}
                  onTouchEnd={e => {
                    const btn = e.currentTarget;
                    btn.style.filter = '';
                  }}
                >
                  {key}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
