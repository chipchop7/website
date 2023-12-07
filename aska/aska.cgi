#!/usr/local/bin/perl

#┌─────────────────────────────────
#│ ASKA BBS : aska.cgi - 2021/07/23
#│ copyright (c) kentweb, 1997-2021
#│ https://www.kent-web.com/
#└─────────────────────────────────

# モジュール宣言
use strict;
use CGI::Carp qw(fatalsToBrowser);

# 設定ファイル認識
require "./init.cgi";
my %cf = set_init();

# データ受理
my %in = parse_form();

# 処理分岐
if ($in{mode} eq 'recv') { recv_data(); }
if ($in{mode} eq 'dele') { dele_data(); }
if ($in{mode} eq 'find') { find_data(); }
if ($in{mode} eq 'note') { note_page(); }
bbs_list();

#-----------------------------------------------------------
#  記事表示
#-----------------------------------------------------------
sub bbs_list {
	my %err = @_;
	
	# 削除フォーム
	if ($in{del}) { del_form(); }
	
	# レス処理
	$in{res} =~ s/\D//g;
	if ($in{res} > 0) {
		my ($flg,$rsub,$rcom);
		open(IN,"$cf{datadir}/log.cgi");
		while (<IN>) {
			my ($no,$sub,$com) = (split(/<>/))[0,4,5];
			if ($in{res} == $no) {
				$flg++;
				$rsub = $sub;
				$rcom = $com;
				last;
			}
		}
		close(IN);
		
		if (!$flg) { error("該当記事が見つかりません"); }
		
		$rsub =~ s/^Re://g;
		$rsub =~ s/\[\d+\]\s?//g;
		$rsub = "Re:[$in{res}] $rsub";
		$rcom = "&gt; $rcom";
		$rcom =~ s|<br( /)?>|\n&gt; |ig;
		
		$in{sub} = $rsub;
		$in{comment} = $rcom;
	}
	
	# ページ数定義
	my $pg = $in{pg} || 0;
	
	# データオープン
	my ($i,@log);
	open(IN,"$cf{datadir}/log.cgi") or error("open err: log.cgi");
	while (<IN>) {
		$i++;
		next if ($i < $pg + 1);
		next if ($i > $pg + $cf{pg_max});
		
		push(@log,$_);
	}
	close(IN);
	
	# 繰越ボタン作成
	my $page_btn = make_pager($i,$pg);
	
	# クッキー取得
	my @cook = get_cookie();
	if ($cook[2] eq '') { $cook[2] = 'http://'; }
	
	# テンプレート読込
	open(IN,"$cf{tmpldir}/bbs.html") or error("open err: bbs.html");
	my $tmpl = join('',<IN>);
	close(IN);
	
	# 文字置換
	$tmpl =~ s/!([a-z]+_cgi)!/$cf{$1}/g;
	$tmpl =~ s/!homepage!/$cf{homepage}/g;
	$tmpl =~ s/<!-- page_btn -->/$page_btn/g;
	$tmpl =~ s/!bbs_title!/$cf{bbs_title}/g;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="$1">|g;
	$tmpl =~ s/!cmnurl!/$cf{cmnurl}/g;
	
	if ($in{job_bak}) {
		$in{comment} =~ s/\t/\n/g;
		$tmpl =~ s/!(name|email|url|sub|comment|pwd)!/$in{$1}/g;
		if (!$in{cookie}) {
			$tmpl =~ s|<input type="checkbox" name="cookie" value="1" checked>|<input type="checkbox" name="cookie" value="1">|;
		}
	} else {
		$tmpl =~ s/!name!/$err{name} ne '' ? $in{name} : $cook[0]/e;
		$tmpl =~ s/!email!/$err{eml} ne '' ? $in{email} : $cook[1]/e;
		$tmpl =~ s/!url!/$err{url} ne '' ? $in{url} : $cook[2]/e;
		$tmpl =~ s/!sub!/$in{sub}/;
		$tmpl =~ s/!comment!/$in{comment}/;
		$tmpl =~ s/!pwd!//;
	}
	
	# 入力エラー時
	if (%err > 0) {
		for (keys %err) { $tmpl =~ s|<!-- err:$_ -->|<div class="err-col">$err{$_}</div>|; }
	}
	
	# テンプレート分割
	my ($head,$loop,$foot) = $tmpl =~ m|(.+)<!-- loop -->(.+?)<!-- /loop -->(.+)|s
			? ($1,$2,$3) : error("テンプレート不正");
	
	# ヘッダ表示
	print "Content-type: text/html; charset=utf-8\n\n";
	print $head;
	
	# ループ部
	for (@log) {
		my ($no,$date,$name,$eml,$sub,$com,$url,undef,undef,undef) = split(/<>/);
		$name = qq|<a href="mailto:$eml">$name</a>| if ($eml);
		$com = autolink($com) if ($cf{autolink});
		$com =~ s/([>]|^)(&gt;[^<]*)/$1<span style="color:$cf{ref_col}">$2<\/span>/g if ($cf{ref_col});
		
		my $tmp = $loop;
		$tmp =~ s/!num!/$no/g;
		$tmp =~ s/!sub!/$sub/g;
		$tmp =~ s/!name!/$name/g;
		$tmp =~ s/!date!/$date/g;
		$tmp =~ s/!comment!/$com/g;
		$tmp =~ s/!bbs_cgi!/$cf{bbs_cgi}/g;
		$tmp =~ s/!home!/home_link($url)/e;
		print $tmp;
	}
	
	# フッタ
	footer($foot);
}

#-----------------------------------------------------------
#  記事受付
#-----------------------------------------------------------
sub recv_data {
	# 戻り
	if ($in{job_bak}) { bbs_list(); }
	
	# 投稿チェック
	check_post();
	
	# 確認画面
	if ($in{job_reg} eq '') {
		conf_form();
	
	# セッション確認
	} else {
		check_ses();
	}
	
	$in{comment} =~ s/\t/<br>/g;
	
	# ホスト取得
	my ($host,$addr) = get_host();
	
	# 削除キー暗号化
	my $pwd = encrypt($in{pwd}) if ($in{pwd} ne "");
	
	# 時間取得
	my $time = time;
	my ($min,$hour,$mday,$mon,$year,$wday) = (localtime($time))[1..6];
	my @wk = ('Sun','Mon','Tue','Wed','Thu','Fri','Sat');
	my $date = sprintf("%04d/%02d/%02d(%s) %02d:%02d",
				$year+1900,$mon+1,$mday,$wk[$wday],$hour,$min);
	
	# 先頭記事読み取り
	open(DAT,"+< $cf{datadir}/log.cgi");
	eval "flock(DAT,2);";
	my $top = <DAT>;
	
	# 重複投稿チェック
	my ($no,$dat,$nam,$eml,$sub,$com,$url,$hos,$pw,$tim) = split(/<>/,$top);
	if ($in{name} eq $nam && $in{comment} eq $com) {
		close(DAT);
		error("二重投稿は禁止です");
	}
	
	# 記事No採番
	$no++;
	
	# 記事数調整
	my @data = ($top);
	my $i = 0;
	while (<DAT>) {
		$i++;
		push(@data,$_);
		
		last if ($i >= $cf{maxlog}-1);
	}
	
	# 更新
	seek(DAT,0,0);
	print DAT "$no<>$date<>$in{name}<>$in{email}<>$in{sub}<>$in{comment}<>$in{url}<>$host<>$pwd<>$time<>\n";
	print DAT @data;
	truncate(DAT,tell(DAT));
	close(DAT);
	
	# クッキー格納
	set_cookie($in{name},$in{email},$in{url}) if ($in{cookie} == 1);
	
	# メール通知
	mail_to($date,$host) if ($cf{mailing} == 1);
	
	# 完了画面
	message("ありがとうございます。記事を受理しました。");
}

#-----------------------------------------------------------
#  確認画面
#-----------------------------------------------------------
sub conf_form {
	# ホスト取得
	my ($host,$addr) = get_host();
	
	open(IN,"$cf{datadir}/log.cgi");
	my $top = <IN>;
	close(IN);
	
	chomp $top;
	my ($no,$dat,$nam,$eml,$sub,$com,$url,$hos,$pw,$tim) = split(/<>/,$top);
	if ($in{name} eq $nam && $in{comment} eq $com) {
		error("二重投稿は禁止です");
	}
	if ($host eq $hos && time - $tim < $cf{wait_time}) {
		error("連続投稿は$cf{wait_time}秒以上空けてください");
	}
	
	# 画像認証用
	my @dig = (0 .. 9);
	my $dig;
	for (1 .. $cf{cap_len}) { $dig .= $dig[int(rand(@dig))]; }
	
	# セッション文字
	my @wd = (0 .. 9, 'a' .. 'z', 'A' .. 'Z', '_');
	my $ses;
	for (1 .. 25) { $ses .= $wd[int(rand(@wd))]; }
	
	# セッションファイル記録
	my $now = time;
	my @log;
	open(DAT,"+< $cf{datadir}/conf.cgi") or error("open err: conf.cgi");
	eval "flock(DAT,2);";
	while(<DAT>) {
		my ($time,$rand,$fig) = split(/\t/);
		next if ($now - $time > $cf{cap_time}*60);
		
		push(@log,$_);
	}
	unshift(@log,"$now\t$ses\t$dig\t$addr\n");
	seek(DAT,0,0);
	print DAT @log;
	truncate(DAT,tell(DAT));
	close(DAT);
	
	# 引数
	my $hid;
	for (qw(name email sub url pwd cookie)) {
		$hid .= qq|<input type="hidden" name="$_" value="$in{$_}">\n|;
	}
	my $com = $in{comment};
	$com =~ s/<br>/\t/g;
	$hid .= qq|<input type="hidden" name="comment" value="$com">\n|;
	$hid .= qq|<input type="hidden" name="ses" value="$ses">\n|;
	
	my $pwd = $in{pwd};
	$pwd =~ s/./*/g;
	
	# テンプレート読み込み
	open(IN,"$cf{tmpldir}/conf.html") or die;
	my $tmpl = join('',<IN>);
	close(IN);
	
	if ($cf{use_captcha} == 0) {
		$tmpl =~ s|<!-- captcha -->.+?<!-- /captcha -->||s;
	}
	$tmpl =~ s/!(bbs_cgi|cmnurl|bbs_title)!/$cf{$1}/g;
	$tmpl =~ s/!(name|email|comment|url|sub)!/$in{$1}/g;
	$tmpl =~ s/!pwd!/$pwd/g;
	$tmpl =~ s/!cookie!/$in{cookie} == 1 ? 'する' : 'しない'/e;
	$tmpl =~ s/<!-- hidden -->/$hid/;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="$1">|g;
	$tmpl =~ s|!captcha!|<img src="$cf{captcha_cgi}?$ses" class="icon" alt="投稿キー">|;
	
	# 画面表記
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  ワード検索
#-----------------------------------------------------------
sub find_data {
	# 条件
	$in{cond} =~ s/\D//g;
	$in{word} =~ s|<br>||g;
	
	# 検索実行
	my @log = search($in{word},$in{cond}) if ($in{word} ne '');
	my $hits = @log;
	
	# テンプレート読み込み
	open(IN,"$cf{tmpldir}/find.html") or error("open err: find.html");
	my $tmpl = join('',<IN>);
	close(IN);
	
	# 文字置換
	$tmpl =~ s/!(bbs_cgi|cmnurl|bbs_title)!/$cf{$1}/g;
	$tmpl =~ s/<!-- op_cond -->/op_cond()/e;
	$tmpl =~ s/!word!/$in{word}/;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="$1">|g;
	if ($in{word} eq '') {
		$tmpl =~ s|<!-- hits_msg -->.+?<!-- /hits_msg -->||s;
	} else {
		$tmpl =~ s/!hits!/$hits/;
	}
	
	# テンプレート分割
	my ($head,$loop,$foot) = $tmpl =~ m|(.+)<!-- loop -->(.+?)<!-- /loop -->(.+)|s
			? ($1,$2,$3) : error("テンプレート不正");
	
	# ヘッダ部
	print "Content-type: text/html; charset=utf-8\n\n";
	print $head;
	
	# ループ部
	for (@log) {
		my ($no,$date,$name,$eml,$sub,$com,$url,undef,undef,undef) = split(/<>/);
		$name = qq|<a href="mailto:$eml">$name</a>| if ($eml);
		$com  = autolink($com) if ($cf{autolink});
		$com  =~ s/([>]|^)(&gt;[^<]*)/$1<span style="color:$cf{ref_col}">$2<\/span>/g if ($cf{ref_col});
		
		my $tmp = $loop;
		$tmp =~ s/!sub!/$sub/g;
		$tmp =~ s/!date!/$date/g;
		$tmp =~ s/!name!/$name/g;
		$tmp =~ s/!home!/home_link($url)/e;
		$tmp =~ s/!comment!/$com/g;
		print $tmp;
	}
	
	# フッタ
	footer($foot);
}

#-----------------------------------------------------------
#  検索実行
#-----------------------------------------------------------
sub search {
	my ($word,$cond) = @_;
	
	# キーワードを配列化
	$word =~ s/　/ /g;
	my @wd = split(/\s+/,$word);
	
	# UTF-8定義
	my $byte1 = '[\x00-\x7f]';
	my $byte2 = '[\xC0-\xDF][\x80-\xBF]';
	my $byte3 = '[\xE0-\xEF][\x80-\xBF]{2}';
	my $byte4 = '[\xF0-\xF7][\x80-\xBF]{3}';
	
	# 検索処理
	my @log;
	open(IN,"$cf{datadir}/log.cgi");
	while (<IN>) {
		my ($no,$date,$nam,$eml,$sub,$com,$url,$hos,$pw,$tim) = split(/<>/);
		
		my $flg;
		foreach my $wd (@wd) {
			if ("$nam $eml $sub $com $url" =~ /^(?:$byte1|$byte2|$byte3|$byte4)*?\Q$wd\E/i) {
				$flg++;
				if ($cond == 0) { last; }
			} else {
				if ($cond == 1) { $flg = 0; last; }
			}
		}
		next if (!$flg);
		
		push(@log,$_);
	}
	close(IN);
	
	# 検索結果
	return @log;
}

#-----------------------------------------------------------
#  検索条件プルダウン
#-----------------------------------------------------------
sub op_cond {
	# 検索条件プルダウン
	my %op = (1 => 'AND', 0 => 'OR');
	my $ret;
	for (1,0) {
		if ($in{cond} eq $_) {
			$ret .= qq|<option value="$_" selected>$op{$_}</option>\n|;
		} else {
			$ret .= qq|<option value="$_">$op{$_}</option>\n|;
		}
	}
	return $ret;
}

#-----------------------------------------------------------
#  留意事項
#-----------------------------------------------------------
sub note_page {
	open(IN,"$cf{tmpldir}/note.html") or error("open err: note.html");
	my $tmpl = join('',<IN>);
	close(IN);
	
	$tmpl =~ s/!cmnurl!/$cf{cmnurl}/g;
	$tmpl =~ s/!bbs_title!/$cf{bbs_title}/g;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="">|g;
	
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  ユーザ記事削除
#-----------------------------------------------------------
sub dele_data {
	$in{del} =~ s/\D//g;
	
	my ($flg,$crypt,@log);
	open(DAT,"+< $cf{datadir}/log.cgi");
	eval "flock(DAT,2);";
	while (<DAT>) {
		my ($no,$dat,$nam,$eml,$sub,$com,$url,$hos,$pw,$tim) = split(/<>/);
		
		if ($in{del} == $no) {
			$flg++;
			$crypt = $pw;
			next;
		}
		push(@log,$_);
	}
	
	if (!$flg or !$crypt) {
		close(DAT);
		error("不正な要求です");
	}
	
	# 削除キーを照合
	if (decrypt($in{pwd},$crypt) != 1) {
		close(DAT);
		error("認証できません");
	}
	
	# ログ更新
	seek(DAT,0,0);
	print DAT @log;
	truncate(DAT,tell(DAT));
	close(DAT);
	
	# 完了
	message("記事を削除しました");
}

#-----------------------------------------------------------
#  削除フォーム
#-----------------------------------------------------------
sub del_form {
	$in{del} =~ s/\D//g;
	my ($flg,$sub);
	open(DAT,"$cf{datadir}/log.cgi");
	while (<DAT>) {
		my ($no,$dat,$nam,$eml,$sb,$com,$url,$hos,$pw,$tim) = split(/<>/);
		
		if ($in{del} == $no) {
			$flg = $pw eq '' ? 1 : 2;
			$sub = $sb;
			last;
		}
	}
	close(IN);
	
	if (!$flg) { error('不正な要求です'); }
	elsif ($flg == 1) { error('この記事は削除できません'); }
	
	open(IN,"$cf{tmpldir}/del.html") or error('open err: del.html');
	my $tmpl = join('',<IN>);
	close(IN);
	
	$tmpl =~ s/!del!/$in{del}/g;
	$tmpl =~ s/!sub!/$sub/;
	$tmpl =~ s/!(bbs_cgi|cmnurl|bbs_title)!/$cf{$1}/g;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="$1">|g;
	$tmpl =~ s/!pg!/$in{pg} eq '' ? '0' : $in{pg}/e;
	
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  エラー画面
#-----------------------------------------------------------
sub error {
	my ($err,$btn) = @_;
	
	open(IN,"$cf{tmpldir}/error.html") or die;
	my $tmpl = join('',<IN>);
	close(IN);
	
	$tmpl =~ s/!error!/$err/g;
	$tmpl =~ s/!(bbs_cgi|cmnurl|bbs_title)!/$cf{$1}/g;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="$1">|g;
	
	if ($btn) {
		$tmpl =~ s|<!-- button -->.+?<!-- /button -->|$btn|s;
	}
	
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  メール送信
#-----------------------------------------------------------
sub mail_to {
	my ($date,$host) = @_;
	
	# 件名をMIMEエンコード
	require "lib/jacode.pl";
	my $msub = mime_unstructured_header("BBS : $in{sub}");
	
	# コメント内の改行復元
	my $com = $in{comment};
	$com =~ s|<br>|\n|g;
	$com =~ s/&lt;/>/g;
	$com =~ s/&gt;/</g;
	$com =~ s/&quot;/"/g;
	$com =~ s/&amp;/&/g;
	$com =~ s/&#39;/'/g;
	
	# メール本文を定義
	my $body = <<EOM;
$cf{bbs_title}に投稿がありました。

投稿日：$date
ホスト：$host

件名  ：$in{sub}
お名前：$in{name}
E-mail：$in{email}
URL   ：$in{url}

$com
EOM

	# JISコード変換
	my $mbody;
	for my $tmp ( split(/\n/,$body) ) {
		jcode::convert(\$tmp,'jis','utf8');
		$mbody .= "$tmp\n";
	}
	
	# メールアドレスがない場合は管理者メールに置き換え
	$in{email} ||= $cf{mailto};
	
	# sendmailコマンド
	my $scmd = "$cf{sendmail} -t -i";
	if ($cf{sendm_f}) { $scmd .= " -f $in{email}"; }
	
	# 送信
	open(MAIL,"| $scmd") or error("送信失敗");
	print MAIL "To: $cf{mailto}\n";
	print MAIL "From: $in{email}\n";
	print MAIL "Subject: $msub\n";
	print MAIL "MIME-Version: 1.0\n";
	print MAIL "Content-type: text/plain; charset=ISO-2022-JP\n";
	print MAIL "Content-Transfer-Encoding: 7bit\n";
	print MAIL "X-Mailer: $cf{version}\n\n";
	print MAIL "$mbody\n";
	close(MAIL);
}

#-----------------------------------------------------------
#  フッター
#-----------------------------------------------------------
sub footer {
	my $foot = shift;
	
	# 著作権表記（削除・改変禁止）
	my $copy = <<EOM;
<p style="margin-top:2em;text-align:center;font-family:Verdana,Helvetica,Arial;font-size:10px;">
	- <a href="https://www.kent-web.com/" target="_top">ASKA BBS</a> -
</p>
EOM

	if ($foot =~ /(.+)(<\/body[^>]*>.*)/si) {
		print "$1$copy$2\n";
	} else {
		print "$foot$copy\n";
		print "</body></html>\n";
	}
	exit;
}

#-----------------------------------------------------------
#  自動リンク
#-----------------------------------------------------------
sub autolink {
	my $text = shift;
	
	$text =~ s/(s?https?:\/\/([\w-.!~*'();\/?:\@=+\$,%#]|&amp;)+)/<a href="$1" target="_blank">$1<\/a>/g;
	return $text;
}

#-----------------------------------------------------------
#  禁止ワードチェック
#-----------------------------------------------------------
sub no_wd {
	my $flg;
	foreach ( split(/,/,$cf{no_wd}) ) {
		if (index("$in{name} $in{sub} $in{comment}", $_) >= 0) {
			$flg = 1;
			last;
		}
	}
	if ($flg) { error("禁止ワードが含まれています"); }
}

#-----------------------------------------------------------
#  URL個数チェック
#-----------------------------------------------------------
sub urlnum {
	my $com = $in{comment};
	my ($num) = ($com =~ s|(https?://)|$1|ig);
	if ($num > $cf{urlnum}) {
		error("コメント中のURLアドレスは最大$cf{urlnum}個までです");
	}
}

#-----------------------------------------------------------
#  アクセス制限
#-----------------------------------------------------------
sub get_host {
	# IP&ホスト取得
	my $host = $ENV{REMOTE_HOST};
	my $addr = $ENV{REMOTE_ADDR};
	if ($cf{gethostbyaddr} && ($host eq "" || $host eq $addr)) {
		$host = gethostbyaddr(pack("C4", split(/\./, $addr)), 2);
	}
	
	# IPチェック
	my $flg;
	foreach ( split(/\s+/,$cf{deny_addr}) ) {
		s/\./\\\./g;
		s/\*/\.\*/g;
		
		if ($addr =~ /^$_/i) { $flg++; last; }
	}
	if ($flg) {
		error("アクセスを許可されていません");
	
	# ホストチェック
	} elsif ($host) {
		
		for ( split(/\s+/,$cf{deny_host}) ) {
			s/\./\\\./g;
			s/\*/\.\*/g;
			
			if ($host =~ /$_$/i) { $flg++; last; }
		}
		if ($flg) {
			error("アクセスを許可されていません");
		}
	}
	
	if ($host eq "") { $host = $addr; }
	return ($host,$addr);
}

#-----------------------------------------------------------
#  crypt暗号
#-----------------------------------------------------------
sub encrypt {
	my $in = shift;
	
	my @wd = (0 .. 9, 'a'..'z', 'A'..'Z', '.', '/');
	my $salt = $wd[int(rand(@wd))] . $wd[int(rand(@wd))];
	crypt($in,$salt) || crypt ($in,'$1$'.$salt);
}

#-----------------------------------------------------------
#  crypt照合
#-----------------------------------------------------------
sub decrypt {
	my ($in,$dec) = @_;
	
	my $salt = $dec =~ /^\$1\$(.*)\$/ ? $1 : substr($dec,0,2);
	if (crypt($in,$salt) eq $dec || crypt($in,'$1$'.$salt) eq $dec) {
		return 1;
	} else {
		return 0;
	}
}

#-----------------------------------------------------------
#  完了メッセージ
#-----------------------------------------------------------
sub message {
	my $msg = shift;
	
	open(IN,"$cf{tmpldir}/mesg.html") or error("open err: mesg.html");
	my $tmpl = join('',<IN>);
	close(IN);
	
	$tmpl =~ s/!(bbs_cgi|cmnurl|bbs_title)!/$cf{$1}/g;
	$tmpl =~ s/!message!/$msg/g;
	$tmpl =~ s|!icon:(\w+\.\w+)!|<img src="$cf{cmnurl}/$1" class="icon" alt="">|g;
	
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  ページ送り作成
#-----------------------------------------------------------
sub make_pager {
	my ($i,$pg) = @_;
	
	# ページ繰越数定義
	$cf{pg_max} ||= 10;
	my $next = $pg + $cf{pg_max};
	my $back = $pg - $cf{pg_max};
	
	# ページ繰越ボタン作成
	my @pg;
	if ($back >= 0 || $next < $i) {
		my $flg;
		my ($w,$x,$y,$z) = (0,1,0,$i);
		while ($z > 0) {
			if ($pg == $y) {
				$flg++;
				push(@pg,qq!<li><a href="#" class="active"><span>$x</span></a></li>\n!);
			} else {
				push(@pg,qq!<li><a href="$cf{bbs_cgi}?pg=$y"><span>$x</span></a></li>\n!);
			}
			$x++;
			$y += $cf{pg_max};
			$z -= $cf{pg_max};
			
			if ($flg) { $w++; }
			last if ($w >= 5 && @pg >= 10);
		}
	}
	while( @pg >= 11 ) { shift(@pg); }
	my $ret = join('', @pg);
	if ($back >= 0) {
		$ret = qq!<li class="pre"><a href="$cf{bbs_cgi}?pg=$back"><span>&laquo;</span></a></li>\n! . $ret;
	}
	if ($next < $i) {
		$ret .= qq!<li class="next"><a href="$cf{bbs_cgi}?pg=$next"><span>&raquo;</span></a></li>\n!;
	}
	
	# 結果を返す
	return $ret ? qq|<div class="pager"><ul class="pagination">\n$ret</ul></div>| : '';
}

#-----------------------------------------------------------
#  クッキー発行
#-----------------------------------------------------------
sub set_cookie {
	my @data = @_;
	
	# 60日間有効
	my ($sec,$min,$hour,$mday,$mon,$year,$wday,undef,undef) = gmtime(time + 60*24*60*60);
	my @mon  = qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec);
	my @week = qw(Sun Mon Tue Wed Thu Fri Sat);
	
	# 時刻フォーマット
	my $gmt = sprintf("%s, %02d-%s-%04d %02d:%02d:%02d GMT",
				$week[$wday],$mday,$mon[$mon],$year+1900,$hour,$min,$sec);
	
	# URLエンコード
	my $cook;
	foreach (@data) {
		s/(\W)/sprintf("%%%02X", unpack("C", $1))/eg;
		$cook .= "$_<>";
	}
	
	print "Set-Cookie: $cf{cookie_id}=$cook; expires=$gmt\n";
}

#-----------------------------------------------------------
#  クッキー取得
#-----------------------------------------------------------
sub get_cookie {
	# クッキー取得
	my $cook = $ENV{HTTP_COOKIE};
	
	# 該当IDを取り出す
	my %cook;
	foreach ( split(/;/,$cook) ) {
		my ($key,$val) = split(/=/);
		$key =~ s/\s//g;
		$cook{$key} = $val;
	}
	
	# URLデコード
	my @cook;
	foreach ( split(/<>/,$cook{$cf{cookie_id}}) ) {
		s/%([0-9A-Fa-f][0-9A-Fa-f])/pack("H2", $1)/eg;
		s/[&"'<>]//g;
		
		push(@cook,$_);
	}
	return @cook;
}

#-----------------------------------------------------------
#  mimeエンコード
#  [quote] http://www.din.or.jp/~ohzaki/perl.htm#JP_Base64
#-----------------------------------------------------------
sub mime_unstructured_header {
  my $oldheader = shift;
  jcode::convert(\$oldheader,'euc','utf8');
  my ($header,@words,@wordstmp,$i);
  my $crlf = $oldheader =~ /\n$/;
  $oldheader =~ s/\s+$//;
  @wordstmp = split /\s+/, $oldheader;
  for ($i = 0; $i < $#wordstmp; $i++) {
    if ($wordstmp[$i] !~ /^[\x21-\x7E]+$/ and
	$wordstmp[$i + 1] !~ /^[\x21-\x7E]+$/) {
      $wordstmp[$i + 1] = "$wordstmp[$i] $wordstmp[$i + 1]";
    } else {
      push(@words, $wordstmp[$i]);
    }
  }
  push(@words, $wordstmp[-1]);
  foreach my $word (@words) {
    if ($word =~ /^[\x21-\x7E]+$/) {
      $header =~ /(?:.*\n)*(.*)/;
      if (length($1) + length($word) > 76) {
	$header .= "\n $word";
      } else {
	$header .= $word;
      }
    } else {
      $header = add_encoded_word($word, $header);
    }
    $header =~ /(?:.*\n)*(.*)/;
    if (length($1) == 76) {
      $header .= "\n ";
    } else {
      $header .= ' ';
    }
  }
  $header =~ s/\n? $//mg;
  $crlf ? "$header\n" : $header;
}
sub add_encoded_word {
  my ($str, $line) = @_;
  my $result;
  my $ascii = '[\x00-\x7F]';
  my $twoBytes = '[\x8E\xA1-\xFE][\xA1-\xFE]';
  my $threeBytes = '\x8F[\xA1-\xFE][\xA1-\xFE]';
  while (length($str)) {
    my $target = $str;
    $str = '';
    if (length($line) + 22 +
	($target =~ /^(?:$twoBytes|$threeBytes)/o) * 8 > 76) {
      $line =~ s/[ \t\n\r]*$/\n/;
      $result .= $line;
      $line = ' ';
    }
    while (1) {
      my $encoded = '=?ISO-2022-JP?B?' .
      b64encode(jcode::jis($target,'euc','z')) . '?=';
      if (length($encoded) + length($line) > 76) {
	$target =~ s/($threeBytes|$twoBytes|$ascii)$//o;
	$str = $1 . $str;
      } else {
	$line .= $encoded;
	last;
      }
    }
  }
  $result . $line;
}
# [quote] http://www.tohoho-web.com/perl/encode.htm
sub b64encode {
    my $buf = shift;
    my ($mode,$tmp,$ret);
    my $b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                . "abcdefghijklmnopqrstuvwxyz"
                . "0123456789+/";
	
    $mode = length($buf) % 3;
    if ($mode == 1) { $buf .= "\0\0"; }
    if ($mode == 2) { $buf .= "\0"; }
    $buf =~ s/(...)/{
        $tmp = unpack("B*", $1);
        $tmp =~ s|(......)|substr($b64, ord(pack("B*", "00$1")), 1)|eg;
        $ret .= $tmp;
    }/eg;
    if ($mode == 1) { $ret =~ s/..$/==/; }
    if ($mode == 2) { $ret =~ s/.$/=/; }
    
    return $ret;
}

#-----------------------------------------------------------
#  Homeリンク
#-----------------------------------------------------------
sub home_link {
	my $url = shift;
	
	return $url ? qq|<a href="$url"><img src="$cf{cmnurl}/home.png" alt="home" class="icon"></a>| : '';
}

#-----------------------------------------------------------
#  入力チェック
#-----------------------------------------------------------
sub check_post {
	# 投稿チェック
	if ($cf{postonly} && $ENV{REQUEST_METHOD} ne 'POST') {
		error("不正なリクエストです");
	}
	
	# 不要改行カット
	$in{sub}  =~ s|<br>||g;
	$in{name} =~ s|<br>||g;
	$in{pwd}  =~ s|<br>||g;
	$in{comment} =~ s|(<br>)+$||g;
	
	if ($cf{no_wd}) { no_wd(); }
	if ($cf{urlnum} > 0) { urlnum(); }
	
	# 未入力の場合
	if ($in{url} eq "http://") { $in{url} = ""; }
	if ($in{sub} eq '') { $in{sub} = '無題'; }
	
	# フォーム内容をチェック
	my %err;
	if ($in{name} eq "") { $err{name} = "名前が入力されていません"; }
	if ($in{email} ne '' && $in{email} !~ /^[\w\.\-]+\@[\w\.\-]+\.[a-zA-Z]{2,6}$/) {
		$err{eml} = "e-mailの入力内容が不正です";
	}
	if ($in{comment} eq "") { $err{com} = "メッセージが入力されていません"; }
	elsif ($cf{jp_wd} && $in{comment} !~ /(?:[\xC0-\xDF][\x80-\xBF]|[\xE0-\xEF][\x80-\xBF]{2}|[\xF0-\xF7][\x80-\xBF]{3})/x) {
		$err{com} = "メッセージに日本語が含まれていません";
	}
	if ($in{url} ne '' && $in{url} !~ /^https?:\/\/[\w-.!~*'();\/?:\@&=+\$,%#]+$/i) {
		$err{url} = "参照先URLの入力内容が不正です";
	}
	if (%err > 0) { bbs_list(%err); }
}

#-----------------------------------------------------------
#  セッション確認
#-----------------------------------------------------------
sub check_ses {
	my $now = time;
	my ($flg,@log);
	open(DAT,"+< $cf{datadir}/conf.cgi");
	eval "flock(DAT,2);";
	while(<DAT>) {
		chomp;
		my ($time,$rand,$fig) = split(/\t/);
		next if ($now - $time > $cf{cap_time}*60);
		
		if ($in{ses} eq $rand) {
			$flg = 1;
			if ($cf{use_captcha} > 0 && $fig ne $in{captcha}) {
				$flg = -1;
				last;
			}
			next;
		}
		push(@log,"$_\n");
	}
	if ($flg == -1) {
		close(DAT);
		error("画像認証できません");
	}
	seek(DAT,0,0);
	print DAT @log;
	truncate(DAT,tell(DAT));
	close(DAT);
	
	if (!$flg) {
		my $msg = "セッションが不正です<br>";
		$msg .= "以下をクリックして再度投稿し直してください\n";
		my $btn .= qq|<input type="button" class="color red button" onclick="window.open('$cf{bbs_cgi}','_self')" value="掲示板に戻る">|;
		error($msg,$btn);
	}
}

