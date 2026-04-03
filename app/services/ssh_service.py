import io
import paramiko
from app.models import Settings
from app.services.crypto import decrypt_data


class SSHService:
    def __init__(self, host, username, port=22):
        self.host = host
        self.username = username
        self.port = port
        self.client = None

    def connect(self):
        """Establish SSH connection using stored private key."""
        encrypted_key = Settings.get('ssh_private_key')
        if not encrypted_key:
            raise ValueError('Klucz SSH nie jest skonfigurowany. Przejdz do Ustawien.')

        private_key_str = decrypt_data(encrypted_key)
        key_file = io.StringIO(private_key_str)

        # Try different key types
        pkey = None
        for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
            try:
                key_file.seek(0)
                pkey = key_class.from_private_key(key_file)
                break
            except paramiko.SSHException:
                continue

        if pkey is None:
            raise ValueError('Nieobslugiwany format klucza SSH')

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            pkey=pkey,
            timeout=30
        )

    def execute_script(self, script_path, remote_name='raport_servera.sh'):
        """Upload and execute script on remote server, then remove it."""
        if not self.client:
            raise RuntimeError('Nie polaczono z serwerem')

        with open(script_path, 'r') as f:
            script_content = f.read()

        sftp = self.client.open_sftp()
        remote_script = f'/tmp/{remote_name}'

        with sftp.file(remote_script, 'w') as remote_file:
            remote_file.write(script_content)

        sftp.chmod(remote_script, 0o755)
        sftp.close()

        stdin, stdout, stderr = self.client.exec_command(f'bash {remote_script}', timeout=120)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        self.client.exec_command(f'rm -f {remote_script}')

        if error and not output:
            raise RuntimeError(error)

        return output if output else error

    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def generate_report(server, script_path='/app/raport_servera.sh'):
    """Generate report for a server."""
    try:
        with SSHService(server.ip_address, server.ssh_user, server.ssh_port) as ssh:
            output = ssh.execute_script(script_path)
            return output, 'success'
    except Exception as e:
        return str(e), 'error'


def run_diagnostics(server, script_path='/app/diagnostics_servera.sh'):
    """Run extended read-only diagnostics on a server. Returns (output, success_bool)."""
    try:
        with SSHService(server.ip_address, server.ssh_user, server.ssh_port) as ssh:
            output = ssh.execute_script(script_path, remote_name='diagnostics_servera.sh')
            return output, True
    except Exception as e:
        return f'Diagnostyka niedostępna: {str(e)}', False
