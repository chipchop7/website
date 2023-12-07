#!/usr/local/bin/perl

#┌─────────────────────────────────
#│ ASKA BBS : admin.cgi - 2022/01/10
#│ copyright (c) kentweb, 1997-2022
#│ https://www.kent-web.com/
#└─────────────────────────────────

# モジュール宣言
use strict;
use CGI::Carp qw(fatalsToBrowser);
use vars qw(%in %cf);
use lib "./lib";
use CGI::Session;
use Digest::SHA::PurePerl qw(sha256_base64);

# 設定ファイル認識
require "./init.cgi";
%cf = set_init();

# データ受理
%in = parse_form();

# 認証
require "./lib/login.pl";
auth_login();

# 処理分岐
if ($in{data_men}) { data_men(); }
if ($in{pass_mgr}) { pass_mgr(); }

# メニュー画面
menu_html();

#-----------------------------------------------------------
#  メニュー画面
#-----------------------------------------------------------
sub menu_html {
	header("メニューTOP");
	print <<EOM;
<div id="body">
<div class="menu-msg">選択ボタンを押してください。</div>
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<table class="form-tbl">
<tr>
	<th>選択</th>
	<th width="280">処理メニュー</th>
</tr><tr>
	<td><input type="submit" name="data_men" value="選択"></td>
	<td>記事データ管理</td>
</tr><tr>
	<td><input type="submit" name="pass_mgr" value="選択"></td>
	<td>パスワード管理</td>
</tr><tr>
	<td><input type="submit" name="logoff" value="選択"></td>
	<td>ログアウト</td>
</tr>
</table>
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  管理モード
#-----------------------------------------------------------
sub data_men {
	# 削除処理
	if ($in{job_dele} && $in{no}) {
		
		# 削除情報
		my %del;
		for ( split(/\0/,$in{no}) ) { $del{$_}++; }
		
		# 削除情報をマッチング
		my @data;
		open(DAT,"+< $cf{datadir}/log.cgi");
		eval "flock(DAT,2);";
		while (<DAT>) {
			my ($no) = (split(/<>/))[0];
			
			if (!defined $del{$no}) {
				push(@data,$_);
			}
		}
		
		# 更新
		seek(DAT,0,0);
		print DAT @data;
		truncate(DAT,tell(DAT));
		close(DAT);
	
	# 修正画面
	} elsif ($in{job_edit} && $in{no}) {
		
		my $log;
		open(IN,"$cf{datadir}/log.cgi");
		while (<IN>) {
			my ($no,$dat,$nam,$eml,$sub,$com,$url,undef,undef,undef) = split(/<>/);
			
			if ($in{no} == $no) {
				$log = $_;
				last;
			}
		}
		close(IN);
		
		# 修正フォームへ
		edit_form($log);
	
	# 修正実行
	} elsif ($in{job} eq "edit") {
		
		# 未入力の場合
		if ($in{url} eq "http://") { $in{url} = ""; }
		$in{sub} ||= "無題";
		
		# 読み出し
		my @data;
		open(DAT,"+< $cf{datadir}/log.cgi");
		eval "flock(DAT,2);";
		while (<DAT>) {
			my ($no,$dat,$nam,$eml,$sub,$com,$url,$hos,$pwd,$tim) = split(/<>/);
			
			if ($in{no} == $no) {
				$_ = "$no<>$dat<>$in{name}<>$in{email}<>$in{sub}<>$in{comment}<>$in{url}<>$hos<>$pwd<>$tim<>\n";
			}
			push(@data,$_);
		}
		
		# 更新
		seek(DAT,0,0);
		print DAT @data;
		truncate(DAT,tell(DAT));
		close(DAT);
	}
	
	# ページ数
	my $page = 0;
	foreach ( keys %in ) {
		if (/^page:(\d+)/) {
			$page = $1;
			last;
		}
	}
	
	# 最大表示件数
	my $logs = 200;
	
	# 削除画面を表示
	header("管理モード");
	print <<EOM;
<div id="body">
<div class="back-btn">
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<input type="submit" value="&lt; メニュー">
</form>
</div>
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="data_men" value="1">
<input type="hidden" name="sid" value="$in{sid}">
<div class="ope-btn">
	<input type="submit" name="job_edit" value="修正">
	<input type="submit" name="job_dele" value="削除">
</div>
EOM

	# 記事を展開
	my $i = 0;
	open(IN,"$cf{datadir}/log.cgi") or error("open err: log.cgi");
	while (<IN>) {
		$i++;
		next if ($i < $page + 1);
		last if ($i > $page + $logs);
		
		my ($no,$dat,$nam,$eml,$sub,$com,$url,$hos,undef,undef) = split(/<>/);
		$nam = qq|<a href="mailto:$eml">$nam</a>| if ($eml);
		
		print qq|<div class="art"><input type="checkbox" name="no" value="$no">\n|;
		print qq|[$no] <strong>$sub</strong> 投稿者：<b>$nam</b> 日時：$dat [ <span>$hos</span> ]</div>\n|;
		print qq|<div class="com">| . cut_str($com,50) . qq|</div>\n|;
	}
	close(IN);
	
	print "</dl>\n";
	
	# ページ繰越定義
	my $next = $page + $logs;
	my $back = $page - $logs;
	if ($back >= 0) {
		print qq|<input type="submit" name="page:$back" value="前ページ">\n|;
	}
	if ($next < $i) {
		print qq|<input type="submit" name="page:$next" value="次ページ">\n|;
	}
	
	print <<EOM;
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  修正フォーム
#-----------------------------------------------------------
sub edit_form {
	my $log = shift;
	my ($no,$dat,$nam,$eml,$sub,$com,$url,undef,undef,undef) = split(/<>/,$log);
	
	$com =~ s|<br( /)?>|\n|g;
	$url ||= "http://";
	
	header("管理モード ＞ 修正フォーム");
	print <<EOM;
<div id="body">
<div class="back-btn">
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="data_men" value="1">
<input type="hidden" name="sid" value="$in{sid}">
<input type="submit" value="&lt; 前画面">
</form>
</div>
<div class="ttl">■ 編集フォーム</div>
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="data_men" value="1">
<input type="hidden" name="job" value="edit">
<input type="hidden" name="no" value="$no">
<input type="hidden" name="sid" value="$in{sid}">
<table class="form-tbl">
<tr>
	<th>おなまえ</th>
	<td><input type="text" name="name" size="35" value="$nam"></td>
</tr><tr>
	<th>Ｅメール</th>
	<td><input type="text" name="email" size="35" value="$eml"></td>
</tr><tr>
	<th>タイトル</th>
	<td><input type="text" name="sub" size="50" value="$sub"></td>
</tr><tr>
	<th>参照先</th>
	<td><input type="text" name="url" size="50" value="$url"></td>
</tr><tr>
	<th>内容</th>
	<td>
		<textarea name="comment" cols="65" rows="8">$com</textarea><br>
		<input type="submit" value="修正する">
	</td>
</tr>
</table>
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  HTMLヘッダー
#-----------------------------------------------------------
sub header {
	my $ttl = shift;
	
	print <<EOM;
Content-type: text/html; charset=utf-8

<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<link href="$cf{cmnurl}/admin.css" rel="stylesheet">
<title>$ttl</title>
</head>
<body>
<div id="head">
	<img src="$cf{cmnurl}/star.png" alt="star" class="icon">
	AskaBBS 管理画面 ::
</div>
EOM
}

#-----------------------------------------------------------
#  エラー
#-----------------------------------------------------------
sub error {
	my $err = shift;
	
	header("ERROR!");
	print <<EOM;
<div id="body">
<div id="err">
<p><b>ERROR!</b></p>
<p class="err">$err</p>
<p><input type="button" value="前画面に戻る" onclick="history.back()"></p>
</div>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  文字カット for UTF-8
#-----------------------------------------------------------
sub cut_str {
	my ($str,$all) = @_;
	$str =~ s|<br( /)?>||g;
	
	my $i = 0;
	my ($ret,$flg);
	while ($str =~ /([\x00-\x7f]|[\xC0-\xDF][\x80-\xBF]|[\xE0-\xEF][\x80-\xBF]{2}|[\xF0-\xF7][\x80-\xBF]{3})/gx) {
		$i++;
		$ret .= $1;
		if ($i >= $all) {
			$flg++;
			last;
		}
	}
	$ret .= '...' if ($flg);
	
	return $ret;
}

